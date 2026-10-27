#include "catalog_lookup.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line%d: %s\n",__LINE__,#x);exit(1);}}while(0)
static uint16_t code[2];static uint32_t trace[128];static unsigned reads;
static M68kStepBusResult fetch(void *unused,uint32_t address,uint16_t *word)
{(void)unused;if(address<0x1000 || address>=0x1004)return M68K_BUS_FAULT;CHECK(reads<128);trace[reads++]=address;*word=code[(address-0x1000)/2];return M68K_BUS_OK;}
static void operation_a(M68kStepContext *c){c->state.regs.D[0]=1;}
static void operation_b(M68kStepContext *c){c->state.regs.D[0]=2;}
static void operation_c(M68kStepContext *c){c->state.regs.D[0]=3;}
static void run_pair(SegaCDCatalogLookup *cache,const M68kStepModule *const *modules,size_t count,
    unsigned expected)
{
    M68kStepContext a,b;M68kStepBus bus={0};bus.fetch16=fetch;
    m68k_step_init(&a,&bus,NULL);m68k_step_init(&b,&bus,NULL);
    a.state.regs.PC=b.state.regs.PC=0x1000;a.state.regs.SR=b.state.regs.SR=0x2700;
    reads=0;M68kStepResult ra=segacd_catalog_execute_slow(&a,modules,count);
    unsigned n=reads;uint32_t expected_trace[128];CHECK(n<=128);
    for(unsigned i=0;i<128;i++)expected_trace[i]=trace[i];
    reads=0;M68kStepResult rb=segacd_catalog_execute(cache,&b,modules,count);
    CHECK(ra==rb && !memcmp(&a.state,&b.state,sizeof a.state));
    CHECK(reads==n);
    for(unsigned i=0;i<n;i++)CHECK(expected_trace[i]==trace[i]);
    if(ra==M68K_STEP_OK)CHECK(b.state.regs.D[0]==expected);
}
int main(void)
{
    static SegaCDCatalogLookup cache;
    M68kStepEntry entries[12]={0};M68kStepModule module[12];const M68kStepModule *list[12];
    for(unsigned i=0;i<12;i++) {
        entries[i].pc=0x1000;entries[i].words[0]=0x303c;entries[i].words[1]=(uint16_t)i;
        entries[i].word_count=2;entries[i].cycles=8;entries[i].execute=operation_a;
        module[i]=(M68kStepModule){"test",0x1000,4,0,&entries[i],1};list[i]=&module[i];
        CHECK(m68k_step_module_valid(&module[i]));
    }
    entries[1].execute=operation_b;entries[2].execute=operation_c;
    code[0]=0x303c;code[1]=1;
    run_pair(&cache,list,3,2);run_pair(&cache,list,3,2);
    code[1]=0;run_pair(&cache,list,3,1); /* previously missing earlier variant */
    code[1]=2;run_pair(&cache,list,3,3); /* unknown suffix discovered lazily */
    code[1]=1;run_pair(&cache,list,3,2);
    code[0]=0xffff;run_pair(&cache,list,3,0); /* current opcode still guarded */
    code[0]=0x303c;code[1]=11;segacd_catalog_lookup_reset(&cache);
    run_pair(&cache,list,12,1);code[1]=0;run_pair(&cache,list,12,1); /* overflow fallback */
    segacd_catalog_lookup_reset(&cache);code[1]=1;
    const M68kStepModule *replacement[]={&module[1]};run_pair(&cache,replacement,1,2);
    segacd_catalog_lookup_reset(&cache);run_pair(&cache,NULL,0,0);
    /* Repeated execution needs one descriptor search rather than 1000. */
    segacd_catalog_lookup_reset(&cache);
    for(unsigned i=0;i<1000;i++)run_pair(&cache,replacement,1,2);
#if SEGACD_CATALOG_LOOKUP_CACHE
    CHECK(cache.descriptor_searches==1 && cache.hits==999);
#endif
    puts("catalog lookup: live opcode/extensions, module order, overflow, registry reset, exact CPU/fetch trace PASS");
    return 0;
}
