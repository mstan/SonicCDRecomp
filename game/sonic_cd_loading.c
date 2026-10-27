/* Original US Sonic CD SP file-engine service.
 *
 * Replace only ReadSectors for complete resident MODE1 requests. The original
 * ISO directory parser, file queue, callers, decompression, Word RAM handoff,
 * music and FMV code still run. This is a synchronous file service, not a CD
 * timing override. The normal guarded native operation remains the fallback.
 */
#include "standalone_services.h"
#include "sector.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { FILE_VARS=0x8c00, READ_SECTORS=0x7afa, READ_SUCCESS=0x7c24,
       CODE_START=0x7800, CODE_BYTES=0x1400, MAX_MODULES=512 };
extern void segacd_boot_sub_at_007AFA(M68kStepContext *);
extern void segacd_boot_sub_at_007C24(M68kStepContext *);

/* The shared machine ABI already permits one active machine per process.
 * These are immutable host assets/dispatch tables, outside serialized state. */
static SegaCDMachine *owner;
static const SegaCDImage *media;
static int enabled;
static FILE *trace;
static unsigned serial;
static uint32_t traced_dest, traced_count;
static M68kStepEntry entries[2];
static M68kStepModule service;
static const M68kStepModule *modules[MAX_MODULES];

static uint16_t get16(const uint8_t *p)
{ return (uint16_t)((unsigned)p[0]*256u+p[1]); }
static uint32_t get32(const uint8_t *p)
{ return (uint32_t)get16(p)*65536u+get16(p+2); }
static void put16(uint8_t *p,uint16_t n)
{ p[0]=(uint8_t)(n>>8);p[1]=(uint8_t)n; }
static void put32(uint8_t *p,uint32_t n)
{ put16(p,(uint16_t)(n>>16));put16(p+2,(uint16_t)n); }
static unsigned bcd(unsigned n) { return (n/10u)*16u+n%10u; }

static int original_code(const SegaCD *cd)
{
    for(unsigned offset=0;offset<CODE_BYTES;offset+=2048u) {
        const uint8_t *raw=segacd_image_resident_sector(media,5+(int32_t)(offset/2048u));
        size_t count=CODE_BYTES-offset;
        if(count>2048u)count=2048u;
        if(!raw || memcmp(cd->prg+CODE_START+offset,raw+16,count))return 0;
    }
    return 1;
}

static uint8_t *destination(SegaCD *cd,uint32_t address,uint32_t bytes,unsigned mode)
{
    if(!bytes || (address&1u))return NULL;
    if(address<SEGACD_PRG_BYTES && bytes<=SEGACD_PRG_BYTES-address) {
        /* Do not overwrite the active BIOS/SP, file variables or file list.
         * GetFiles legitimately uses its own one-sector directory buffer. */
        if(address<(unsigned)cd->write_protect*512u)return NULL;
        if(address<0xb600u && !(mode==1 && address==0xad00u && bytes==2048u))return NULL;
        return cd->prg+address;
    }
    if(address>=0x80000u && address<0xc0000u && bytes<=0xc0000u-address &&
       !(cd->memory_mode&5u)) /* 2M mode, Sub owns Word RAM */
        return cd->word+address-0x80000u;
    return NULL;
}

static void trace_begin(const SegaCD *cd)
{
    if(!trace)return;
    if(serial>=1024u){traced_count=0;return;}
    const uint8_t *v=cd->prg+FILE_VARS;
    traced_dest=get32(v+0x10);traced_count=get32(v+8);
    fprintf(trace,"{\"event\":\"begin\",\"id\":%u,\"frame\":%llu,\"lba\":%u,\"count\":%u,\"dest\":%u,\"mode\":%u}\n",
        ++serial,(unsigned long long)owner->frames,get32(v+4),traced_count,traced_dest,get16(v+0x1c));
    fflush(trace);
}

static void trace_success(const SegaCD *cd)
{
    if(!trace || !traced_count)return;
    const uint8_t *v=cd->prg+FILE_VARS;
    uint64_t hash=UINT64_C(14695981039346656037);
    uint8_t *data=traced_count<=256u ? destination((SegaCD *)cd,traced_dest,traced_count*2048u,get16(v+0x1c)) : NULL;
    if(data)for(uint32_t i=0;i<traced_count*2048u;++i)hash=(hash^data[i])*UINT64_C(1099511628211);
    fprintf(trace,"{\"event\":\"success\",\"id\":%u,\"frame\":%llu,\"lba\":%u,\"count\":%u,\"dest\":%u,\"time\":%u,\"wait\":%u,\"retries\":%u,\"read\":%u,\"sector_frame\":%u,\"hash\":\"%016llx\"}\n",
        serial,(unsigned long long)owner->frames,get32(v+4),get32(v+8),get32(v+0x10),get32(v+0x14),
        get16(v+0x22),get16(v+0x24),get16(v+0x26),v[0x29],(unsigned long long)hash);
    fflush(trace);
}

static int resident_read(M68kStepContext *ctx)
{
    SegaCD *cd=&owner->devices;
    uint8_t *v=cd->prg+FILE_VARS;
    unsigned mode=get16(v+0x1c);
    uint32_t lba=get32(v+4),count=get32(v+8),address=get32(v+0x10);
    uint32_t sp=ctx->state.regs.A[7];
    if(!enabled || ctx!=&owner->coordinator.cpu[SEGACD_SUB] ||
       ctx->state.regs.A[5]!=FILE_VARS || (mode!=1 && mode!=2) || v[0x28]!=3 ||
       !count || count>256u || lba>449849u-count ||
       sp>SEGACD_PRG_BYTES-4u || (sp&1u) ||
       FILE_VARS<(unsigned)cd->write_protect*512u || !original_code(cd))return 0;
    uint32_t ret=get32(cd->prg+sp);
    if(ret<CODE_START || ret>=READ_SECTORS || (ret&1u))return 0;
    uint32_t bytes=count*2048u;
    uint8_t *out=destination(cd,address,bytes,mode);
    if(!out || (address<sp+4u && address+bytes>sp))return 0;
    /* Preflight the ENTIRE request before any guest-visible change. Bad EDC,
     * absent residency, unsupported mode/ownership all retain original code. */
    for(uint32_t i=0;i<count;++i) {
        const uint8_t *raw=segacd_image_resident_sector(media,(int32_t)(lba+i));
        unsigned time=lba+i+150u;
        if(!raw || segacd_sector_validate(raw)!=SEGACD_SECTOR_MODE1_OK ||
           raw[12]!=bcd(time/4500u) || raw[13]!=bcd(time/75u%60u) || raw[14]!=bcd(time%75u))return 0;
    }
    for(uint32_t i=0;i<count;++i)
        memcpy(out+i*2048u,segacd_image_resident_sector(media,(int32_t)(lba+i))+16,2048u);
    const uint8_t *last=segacd_image_resident_sector(media,(int32_t)(lba+count-1u));
    put32(v,0x7b4eu); /* native coroutine's sector-ready bookmark */
    put32(v+4,lba+count);put32(v+8,0);put32(v+0xc,ret);
    put32(v+0x10,address+bytes);memcpy(v+0x14,last+12,4);
    put16(v+0x22,6);put16(v+0x24,30);put16(v+0x26,(uint16_t)count);
    v[0x29]=(uint8_t)bcd((lba+count)%75u);
    ctx->state.regs.A[7]=sp+4u;
    /* Execute the original success/CDC selection/return instructions next.
     * Callers reset the operation and perform their own normal handshakes. */
    ctx->state.regs.PC=READ_SUCCESS;
    return 1;
}

static void read_sectors(M68kStepContext *ctx)
{
    trace_begin(&owner->devices);
    if(!resident_read(ctx))segacd_boot_sub_at_007AFA(ctx);
}
static void read_success(M68kStepContext *ctx)
{
    trace_success(&owner->devices);
    segacd_boot_sub_at_007C24(ctx);
}

void segacd_standalone_services_install(SegaCDMachine *machine,const SegaCDImage *image)
{
    owner=machine;media=image;serial=0;
    const char *disable=getenv("SONIC_CD_LOADING_ORIGINAL");
    const char *log=getenv("SONIC_CD_LOADING_TRACE");
    enabled=!(disable && !strcmp(disable,"1"));
    if(log && *log)trace=fopen(log,"w");
    SegaCDCoordinator *c=&machine->coordinator;
    if(c->module_count[SEGACD_SUB]>=MAX_MODULES || !segacd_image_resident_sector(image,7))return;
    const uint32_t pcs[2]={READ_SECTORS,READ_SUCCESS};
    const unsigned words[2]={2,3},cycles[2]={24,16};
    for(unsigned i=0;i<2;++i) {
        uint32_t offset=pcs[i]-CODE_START;
        const uint8_t *raw=segacd_image_resident_sector(image,5+(int32_t)(offset/2048u));
        if(!raw)return;
        entries[i].pc=pcs[i];entries[i].word_count=(uint8_t)words[i];entries[i].cycles=(uint16_t)cycles[i];
        for(unsigned j=0;j<words[i];++j)entries[i].words[j]=get16(raw+16+offset%2048u+j*2u);
    }
    entries[0].execute=read_sectors;entries[1].execute=read_success;
    service.name="Sonic CD resident file service";service.image_base=CODE_START;service.image_size=CODE_BYTES;
    service.entries=entries;service.count=2;
    modules[0]=&service;
    size_t count=c->module_count[SEGACD_SUB];
    memcpy(modules+1,c->modules[SEGACD_SUB],count*sizeof(*modules));
    if(!segacd_coordinator_modules(c,SEGACD_SUB,modules,count+1u))
        fprintf(stderr,"Resident file service unavailable; original program retained.\n");
}
