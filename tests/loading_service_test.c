/* Service contract tests use synthetic sectors, never owned disc/BIOS data. */
#include "../game/sonic_cd_loading.c"
#define CHECK(x) do { if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);} } while(0)
static uint8_t sectors[32][2352];
static SegaCDMachine machine;
static SegaCD saved;
static M68kStepState saved_cpu;
static unsigned fallback;

const uint8_t *segacd_image_resident_sector(const SegaCDImage *image,int32_t lba)
{ (void)image;return lba>=0 && lba<32 ? sectors[lba] : NULL; }
int segacd_coordinator_modules(SegaCDCoordinator *c,SegaCDCpu cpu,
                              const M68kStepModule *const *m,size_t count)
{ c->modules[cpu]=m;c->module_count[cpu]=count;return 1; }
void segacd_boot_sub_at_007AFA(M68kStepContext *ctx) { (void)ctx;++fallback; }
void segacd_boot_sub_at_007C24(M68kStepContext *ctx) { (void)ctx; }

static void sector(unsigned lba)
{
    uint8_t *p=sectors[lba];memset(p,0,2352);memset(p+1,255,10);
    unsigned t=lba+150u;
    p[12]=(uint8_t)bcd(t/4500u);p[13]=(uint8_t)bcd(t/75u%60u);p[14]=(uint8_t)bcd(t%75u);p[15]=1;
    for(unsigned i=16;i<2064;++i)p[i]=(uint8_t)(i+lba);
    uint32_t crc=0;
    for(unsigned i=0;i<2064;++i) {
        crc^=p[i];for(unsigned bit=0;bit<8;++bit)crc=(crc>>1)^((crc&1u)?0xd8018001u:0);
    }
    for(unsigned i=0;i<4;++i)p[2064+i]=(uint8_t)(crc>>(8u*i));
}
static M68kStepContext *prepare(unsigned mode,uint32_t dest,uint32_t count)
{
    memset(&machine,0,sizeof machine);owner=&machine;media=NULL;enabled=1;trace=NULL;
    for(unsigned i=0;i<32;++i)sector(i);
    for(unsigned offset=0;offset<CODE_BYTES;offset+=2048u) {
        size_t n=CODE_BYTES-offset;if(n>2048)n=2048;
        memcpy(machine.devices.prg+CODE_START+offset,sectors[5+offset/2048]+16,n);
    }
    uint8_t *v=machine.devices.prg+FILE_VARS;
    put32(v+4,16);put32(v+8,count);put32(v+0x10,dest);put16(v+0x1c,(uint16_t)mode);v[0x28]=3;
    M68kStepContext *c=&machine.coordinator.cpu[SEGACD_SUB];
    c->state.regs.A[5]=FILE_VARS;c->state.regs.A[7]=0x5e00;c->state.regs.PC=READ_SECTORS+4;
    put32(machine.devices.prg+0x5e00,0x7a00);
    return c;
}
static void miss_unchanged(M68kStepContext *c)
{
    saved=machine.devices;saved_cpu=c->state;
    CHECK(!resident_read(c));
    CHECK(!memcmp(&saved,&machine.devices,sizeof saved));
    CHECK(!memcmp(&saved_cpu,&c->state,sizeof saved_cpu));
    unsigned old=fallback;read_sectors(c);CHECK(fallback==old+1);
}
int main(void)
{
    M68kStepContext *c=prepare(2,0x80000,2);
    saved=machine.devices;
    CHECK(resident_read(c));
    CHECK(!memcmp(&saved.drive,&machine.devices.drive,sizeof saved.drive));
    CHECK(!memcmp(&saved.cdc,&machine.devices.cdc,sizeof saved.cdc));
    CHECK(!memcmp(&saved.cdda,&machine.devices.cdda,sizeof saved.cdda));
    CHECK(!memcmp(&saved.pcm,&machine.devices.pcm,sizeof saved.pcm));
    CHECK(saved.sub_cycles==machine.devices.sub_cycles);
    CHECK(!memcmp(machine.devices.word,sectors[16]+16,2048));
    CHECK(!memcmp(machine.devices.word+2048,sectors[17]+16,2048));
    uint8_t *v=machine.devices.prg+FILE_VARS;
    CHECK(get32(v+4)==18 && get32(v+8)==0 && get32(v+0x10)==0x81000);
    CHECK(get32(v+0xc)==0x7a00 && !memcmp(v+0x14,sectors[17]+12,4));
    CHECK(get16(v+0x22)==6 && get16(v+0x24)==30 && get16(v+0x26)==2);
    CHECK(c->state.regs.PC==READ_SUCCESS && c->state.regs.A[7]==0x5e04);
    c=prepare(1,0xad00,1);CHECK(resident_read(c));CHECK(!memcmp(machine.devices.prg+0xad00,sectors[16]+16,2048));
    c=prepare(2,0x20000,2);CHECK(resident_read(c));CHECK(!memcmp(machine.devices.prg+0x20000,sectors[16]+16,2048));
    c=prepare(2,0x80000,2);sectors[17][100]^=1;miss_unchanged(c); /* last sector invalid: no partial write */
    c=prepare(2,0x80000,2);memcpy(sectors[17],sectors[18],2352);miss_unchanged(c); /* valid EDC, wrong sector address */
    c=prepare(2,0x80000,2);machine.devices.memory_mode=1;miss_unchanged(c);
    c=prepare(2,0x80000,2);machine.devices.memory_mode=4;miss_unchanged(c);
    c=prepare(2,0xbf800,2);miss_unchanged(c);
    c=prepare(2,0x7f800,2);miss_unchanged(c);
    c=prepare(2,0xff0000,1);miss_unchanged(c); /* PCM is not ordinary RAM */
    c=prepare(2,0x8c00,1);miss_unchanged(c); /* file vars/code cannot be destroyed */
    c=prepare(2,0xad00,1);miss_unchanged(c); /* directory exception only for GetFiles */
    c=prepare(3,0x80000,1);miss_unchanged(c); /* FMV remains original */
    c=prepare(2,0x80000,0);miss_unchanged(c);
    c=prepare(2,0x80000,UINT32_MAX);miss_unchanged(c);
    c=prepare(2,0x80000,1);put32(machine.devices.prg+FILE_VARS+4,32);miss_unchanged(c);
    c=prepare(2,0x80000,1);machine.devices.prg[CODE_START+3000]^=1;miss_unchanged(c);
    c=prepare(2,0x80000,1);machine.devices.write_protect=255;miss_unchanged(c);
    c=prepare(2,0x80000,1);enabled=0;miss_unchanged(c);
    puts("Resident loading service preflight, writes and original fallback passed");return 0;
}
