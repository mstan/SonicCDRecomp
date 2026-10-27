/* Reuse the upstream synthetic contract, then compare against its unchanged
 * scalar renderer on randomized live-raster/published-world inputs. */
#define main upstream_renderer_contract
#include "../external/segagenesisrecomp/tests/segacd/sonic_cd_render_test.c"
#undef main
extern int reference_render(const SegaCDRender *,const GVDP *,unsigned,uint32_t *,size_t);
static uint32_t rng=0x47553291u;
static uint32_t random_word(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
int main(void)
{
    CHECK(upstream_renderer_contract()==0);
    enum{MAX=SEGACD_SONIC_CD_MAX_VIEW_WIDTH};
    static uint32_t eager[MAX],spans[MAX];
    static uint8_t old_sprites[MAX],new_sprites[MAX];
    SegaCDScenePiece pieces[24];SegaCDScene scene;
    unsigned widths[]={320,321,398,400,523,796,MAX};
    for(unsigned trial=0;trial<4000;trial++) {
        init_synthetic_world();empty_scene(&scene);memset(pieces,0,sizeof pieces);
        unsigned width=widths[trial%7],line=random_word()%224;
        unsigned camera=trial<128?(trial&15)*256:random_word()&8191u;
        put_be16(main_ram+0x1926,(uint16_t)camera);
        put_be16(main_ram+0x192a,(uint16_t)random_word());
        put_be16(main_ram+0x1936,(uint16_t)random_word());
        put_be16(main_ram+0x193a,(uint16_t)random_word());
        for(unsigned i=0;i<64;i++)vdp.cram[i]=(uint16_t)random_word();
        for(unsigned i=0;i<64*32;i++)vdp.vram[i]=(uint8_t)random_word();
        for(unsigned block=0;block<3;block++)for(unsigned part=0;part<4;part++)
            put_be16(main_ram+0x2000+block*8+part*2,
                (uint16_t)((random_word()&0xf800u)|(random_word()&63u)));
        vdp.reg[16]=(uint8_t)((trial%4)|((trial/4%4)<<4));
        vdp.reg[11]=(uint8_t)(trial%4);
        vdp.reg[12]=(uint8_t)(1|((trial&1)?8:0));
        vdp.vsram[0]=(uint16_t)random_word();vdp.vsram[1]=(uint16_t)random_word();
        unsigned hrow=(vdp.reg[11]&3)==0?0:(vdp.reg[11]&3)==2?line&~7u:line;
        put_be16(vdp.vram+0x8000+hrow*4,(uint16_t)random_word());
        put_be16(vdp.vram+0x8002+hrow*4,(uint16_t)random_word());
        scene.pieces=pieces;scene.piece_capacity=24;scene.piece_count=trial%25;
        for(unsigned i=0;i<scene.piece_count;i++) {
            pieces[i].x=(int16_t)((int)(random_word()%(width+128))-64);
            pieces[i].y=(int16_t)((int)line-(int)(random_word()%40)+20);
            pieces[i].size=(uint8_t)(random_word()&15u);
            pieces[i].tile_attribute=(uint16_t)((random_word()&0xf800u)|(random_word()&63u));
            pieces[i].hud_slot=(uint8_t)(random_word()&1u);
            pieces[i].screen_relative=(uint8_t)(random_word()&1u);
        }
        if(trial%37==0)vdp.reg[12]=0; /* early rejection leaves both buffers */
        if(trial%41==0)world.level_chunks_address=0x23ffff; /* late invalid source */
        if(trial%43==0)scene.status=SEGACD_SCENE_INVALID_SNAPSHOT;
        memset(eager,0xa5,sizeof eager);memset(spans,0xa5,sizeof spans);
        memset(old_sprites,0x5a,sizeof old_sprites);memset(new_sprites,0x5a,sizeof new_sprites);
        SegaCDRender a={&world,&scene,width,old_sprites,MAX},b={&world,&scene,width,new_sprites,MAX};
        int ra=reference_render(&a,&vdp,line,eager,MAX);
        int rb=segacd_render_scanline(&b,&vdp,line,spans,MAX);
        if(ra!=rb || memcmp(eager,spans,sizeof eager) || memcmp(old_sprites,new_sprites,sizeof old_sprites)) {
            fprintf(stderr,"differential trial%u width%u line%u return%d/%d\n",trial,width,line,ra,rb);return 1;
        }
    }
    puts("Sonic CD renderer 4000 scalar/span raster+scratch/rejection cases PASS");return 0;
}
