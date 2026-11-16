#include "NG2DeviceRaster.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define PIXELS (896u*414u)
static int overlaps(double x0,double y0,double x1,double y1,NG2DeviceRect b){
    return x0<b.x1&&b.x0<x1&&y0<b.y1&&b.y0<y1;
}
static int rect_valid(NG2DeviceRect b,double w,double h){
    return isfinite(b.x0)&&isfinite(b.y0)&&isfinite(b.x1)&&isfinite(b.y1)
        &&0<=b.x0&&b.x0<b.x1&&b.x1<=w&&0<=b.y0&&b.y0<b.y1&&b.y1<=h;
}
static int hidden(int x0,int y0,int x1,int y1,const NG2DeviceGeometryProfile *p,
    const NG2DeviceRect *occlusions,size_t count,int world){
    for(size_t i=0;i<count;i++)if(overlaps(x0*.5,y0*.5,x1*.5,y1*.5,occlusions[i]))return 1;
    if(world)for(size_t i=0;i<p->source_hud_count;i++)
        if(overlaps(x0*.5,y0*.5,x1*.5,y1*.5,p->source_hud[i].source_points))return 1;
    return 0;
}
static double cubic(double x){
    x=fabs(x);if(x<1)return ((x-2)*x)*x+1;
    return x<2?((-x+5)*x-8)*x+4:0;
}
/* Sampling is explicit, bounded and has no edge-clamp fallback. BOX follows
 * the measured 2x separable rounding phase; bilinear/cubic truncate like the
 * tested Pillow affine preview. Actual ImageIO source bytes remain unaccepted. */
static int sample(const uint8_t *s,int sampler,double left,double top,double right,double bottom,
    uint8_t out[4],const NG2DeviceGeometryProfile *p,const NG2DeviceRect *occlusions,size_t count,int world){
    double cx=(left+right)*.5,cy=(top+bottom)*.5,qx=cx-.5,qy=cy-.5;
    int x0,x1,y0,y1;
    if(sampler==NG2_DEVICE_UI_NEAREST){x0=x1=(int)floor(cx);y0=y1=(int)floor(cy);}
    else if(sampler==NG2_DEVICE_UI_BOX){
        double rx=fmax(1,right-left)*.5,ry=fmax(1,bottom-top)*.5;
        /* Pillow resize BOX: selected pixel centres are (left,right], with
         * the kernel widened for reduction. Partial edge areas are not used. */
        x0=(int)floor(cx-rx+.5);x1=(int)floor(cx+rx+.5)-1;
        y0=(int)floor(cy-ry+.5);y1=(int)floor(cy+ry+.5)-1;
    }
    else if(sampler==NG2_DEVICE_UI_BILINEAR||sampler==NG2_DEVICE_UI_BICUBIC){
        x0=x1=(int)floor(qx);y0=y1=(int)floor(qy);
        if(qx!=floor(qx)){x1++;if(sampler==NG2_DEVICE_UI_BICUBIC){x0--;x1++;}}
        if(qy!=floor(qy)){y1++;if(sampler==NG2_DEVICE_UI_BICUBIC){y0--;y1++;}}
    }else return 0;
    if(x0<0||y0<0||x1>=1334||y1>=750||hidden(x0,y0,x1+1,y1+1,p,occlusions,count,world))return 0;
    for(int channel=0;channel<3;channel++){
        double sum=0,wy_total=0;
        for(int y=y0;y<=y1;y++){
            double wy=1,row=0,wx_total=0;
            if(sampler==NG2_DEVICE_UI_BILINEAR)wy=fmax(0,1-fabs(y-qy));
            else if(sampler==NG2_DEVICE_UI_BICUBIC)wy=cubic(y-qy);
            for(int x=x0;x<=x1;x++){
                double wx=1;
                if(sampler==NG2_DEVICE_UI_BILINEAR)wx=fmax(0,1-fabs(x-qx));
                else if(sampler==NG2_DEVICE_UI_BICUBIC)wx=cubic(x-qx);
                row+=wx*s[((size_t)y*1334+(size_t)x)*4+(size_t)channel];wx_total+=wx;
            }
            if(sampler==NG2_DEVICE_UI_BOX)row=floor(row/wx_total+.5);else row/=wx_total;
            sum+=wy*row;wy_total+=wy;
        }
        sum/=wy_total;if(sampler==NG2_DEVICE_UI_BOX)sum=floor(sum+.5);
        out[channel]=(uint8_t)fmax(0,fmin(255,sum));
    }
    out[3]=255;return 1;
}
static void black(uint8_t *r,size_t pixel){memset(r+4*pixel,0,3);r[4*pixel+3]=255;}
int ng2_profile_raster8(const uint8_t *s,size_t n,int32_t w,int32_t h,
    const NG2DeviceGeometryProfile *p,const NG2DeviceRect *o,size_t count,int32_t view,
    uint8_t *r,size_t rn,uint8_t *observed,size_t on,NG2ProfileRasterValidity *v){
    if(!s||!r||!observed||!v||!p||w!=1334||h!=750||n!=1334u*750u*4u||rn!=PIXELS*4u||on!=PIXELS
        ||p->device!=8||p->legacy_passthrough||p->panel_width!=375||p->panel_height!=667
        ||p->source_point_width!=667||p->source_point_height!=375
        ||p->canonical_width!=896||p->canonical_height!=414||!p->ui_maps||p->ui_map_count>16
        ||!p->source_hud||p->source_hud_count>32||count>16||(count&&!o)
        ||(view!=NG2_PROFILE_RASTER_FLOOR&&view!=NG2_PROFILE_RASTER_PAUSE)
        ||p->world_to_canonical.a!=1||p->world_to_canonical.b!=0||p->world_to_canonical.c!=0
        ||p->world_to_canonical.d!=1||!isfinite(p->world_to_canonical.tx)||!isfinite(p->world_to_canonical.ty)
        ||fabs(p->world_to_canonical.tx)>4096||fabs(p->world_to_canonical.ty)>4096
        ||p->canonical_source_fov.x0!=p->world_to_canonical.tx||p->canonical_source_fov.y0!=p->world_to_canonical.ty
        ||p->canonical_source_fov.x1-p->canonical_source_fov.x0!=667
        ||p->canonical_source_fov.y1-p->canonical_source_fov.y0!=375)return -1;
    for(size_t i=3;i<n;i+=4)if(s[i]!=255)return -1;
    for(size_t i=0;i<count;i++)if(!rect_valid(o[i],667,375))return -1;
    for(size_t i=0;i<p->source_hud_count;i++)if(!rect_valid(p->source_hud[i].source_points,667,375))return -1;
    for(size_t i=0;i<p->ui_map_count;i++)if(!p->ui_maps[i].name
        ||!rect_valid(p->ui_maps[i].source_points,667,375)
        ||!rect_valid(p->ui_maps[i].canonical,896,414))return -1;
    memset(v,0,sizeof(*v));v->version=1;v->size=sizeof(*v);v->qualification_gaps=p->qualification_gaps;
    v->clear_scope=count==0?NG2_CLEAR_SCOPE_OBSERVED_FOV_MINUS_HUD:NG2_CLEAR_SCOPE_UNKNOWN;
    memset(observed,0,on);for(size_t i=0;i<PIXELS;i++)black(r,i);
    const double tx=p->world_to_canonical.tx,ty=p->world_to_canonical.ty;
    for(int y=0;y<414;y++)for(int x=0;x<896;x++){
        size_t at=(size_t)y*896+(size_t)x;
        observed[at]=(uint8_t)sample(s,NG2_DEVICE_UI_BOX,(x-tx)*2,(y-ty)*2,
            (x+1-tx)*2,(y+1-ty)*2,r+at*4,p,o,count,1);
    }
    /* Full 36x36 cell support covers the material lower bands as well as the
     * central25x25. Unsupported cells are unknown, never observed black floor. */
    for(int j=-5;j<5;j++)for(int i=-11;i<12;i++){
        int cx=448+36*i,cy=207+36*j,ok=1;
        for(int y=cy-18;y<cy+18&&ok;y++)for(int x=cx-18;x<cx+18;x++)
            if(x<0||y<0||x>=896||y>=414||!observed[(size_t)y*896+(size_t)x]){ok=0;break;}
        v->cell_observed[(j+5)*23+i+11]=(uint8_t)ok;
        /* Preserve actually observed fragments for global pixel scans. Only
         * the derived tile label is excluded after public C classification. */
    }
    int required=0,all=1,restarts=0,restart_ok=1;
    for(size_t k=0;k<p->ui_map_count;k++){
        const NG2DeviceUIMap *m=&p->ui_maps[k];
        int resume=strstr(m->name,"continue")!=NULL,restart=strstr(m->name,"restart")!=NULL;
        int pause=resume||restart;
        if(pause!=(view==NG2_PROFILE_RASTER_PAUSE))continue;
        int ok=1;
        for(int y=(int)floor(m->canonical.y0);y<(int)ceil(m->canonical.y1);y++)
            for(int x=(int)floor(m->canonical.x0);x<(int)ceil(m->canonical.x1);x++){
                if(x+.5<m->canonical.x0||x+.5>=m->canonical.x1||y+.5<m->canonical.y0||y+.5>=m->canonical.y1)continue;
                double sx=(m->source_points.x1-m->source_points.x0)/(m->canonical.x1-m->canonical.x0);
                double sy=(m->source_points.y1-m->source_points.y0)/(m->canonical.y1-m->canonical.y0);
                double left=(m->source_points.x0+(x-m->canonical.x0)*sx)*2;
                double top=(m->source_points.y0+(y-m->canonical.y0)*sy)*2;
                size_t at=(size_t)y*896+(size_t)x;
                if(!sample(s,m->resampler,left,top,left+sx*2,top+sy*2,r+at*4,p,o,count,0)){black(r,at);ok=0;}
            }
        v->ui_observed[k]=(uint8_t)ok;
        /* The beat fit sees a partially observed horizontal FOV. It remains
         * diagnostic; it is not a UI-state guard or a timing qualification. */
        if((view==NG2_PROFILE_RASTER_PAUSE&&resume)||(view==NG2_PROFILE_RASTER_FLOOR&&strcmp(m->name,"beat"))){required++;all&=ok;}
        if(restart){restarts++;restart_ok&=ok;}
    }
    v->ui_state_observed=required>0&&all;
    v->restart_ui_observed=restarts>0&&restart_ok;
    return 0;
}
static void unknown_scene(NG2Scene *s){memset(s,0,sizeof(*s));s->abi_version=1;s->struct_size=sizeof(*s);}
int ng2_profile_goods_support(const NG2Scene *scene,const uint8_t *observed,size_t length,NG2DeviceRect *required){
    if(!scene||!observed||length!=PIXELS||!required||scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE)return 0;
    int n=0,minx=12,maxx=-12,row=-9;
    for(int j=-5;j<5;j++)for(int i=-11;i<12;i++)if(scene->tiles[(j+5)*23+i+11]==NG2_TILE_ITEM){
        if(n&&row!=j)return 0;
        row=j;n++;if(i<minx)minx=i;if(i>maxx)maxx=i;
    }
    if(n!=3||maxx-minx!=2)return 0;
    /* Invert only the existing even-rounding bins, not colour recognition:
     * cx within cell centre +/-18; sy=159+36*row +/-18. All possible sign
     * density14 taps, item rectangles, and price windows then fit this union.
     * Unknown pixels anywhere in that union deny the whole-three proof. */
    *required=(NG2DeviceRect){448+36*minx-36,121+36*row,448+36*maxx+36,266+36*row};
    if(!rect_valid(*required,896,414))return 0;
    for(int y=(int)required->y0;y<(int)required->y1;y++)
        for(int x=(int)required->x0;x<(int)required->x1;x++)if(!observed[(size_t)y*896+(size_t)x])return 0;
    return 1;
}
static int valid(const NG2ProfileRasterValidity *v){return v&&v->version==1&&v->size==sizeof(*v);}
void ng2_profile_restrict_scene(NG2Scene *scene,NG2ProfileRasterValidity *v,const uint8_t *observed){
    if(!scene||!valid(v)||!observed||scene->state!=NG2_FLOOR)return;
    for(int i=0;i<NG2_TILE_COUNT;i++)if(!v->cell_observed[i])scene->tiles[i]=NG2_TILE_UNKNOWN;
    /* protected_cells marks positive merchandise/unsafe evidence. Missing FOV
     * is UNKNOWN terrain, not invented merchandise protection. Never erase a
     * positive protected bit supplied by the unchanged classifier. */
    NG2DeviceRect required;
    v->goods_coverage_qualified=ng2_profile_goods_support(scene,observed,PIXELS,&required);
    if(!v->goods_coverage_qualified)scene->goods=NG2_GOODS_UNKNOWN;
    if(scene->gold_state==NG2_GOLD_CLEAR&&v->clear_scope!=NG2_CLEAR_SCOPE_OBSERVED_FOV_MINUS_HUD)
        scene->gold_state=NG2_GOLD_UNKNOWN;
}
int ng2_profile_raster_analyze(const uint8_t *floor_rgba,const uint8_t *floor_observed,const NG2ProfileRasterValidity *fv,
    const uint8_t *pause_rgba,const NG2ProfileRasterValidity *pv,NG2Scene *scene,int32_t *selected,NG2ProfileRasterValidity *chosen){
    if(!scene||!selected||!chosen)return -1;
    unknown_scene(scene);*selected=NG2_PROFILE_RASTER_FLOOR;
    memset(chosen,0,sizeof(*chosen));
    if(!floor_rgba||!floor_observed||!pause_rgba||!valid(fv)||!valid(pv))return -1;
    *chosen=*fv;
    if(pv->ui_state_observed){
        if(ng2_analyze_rgba(pause_rgba,PIXELS*4u,896u*4u,scene))return -1;
        if(scene->state==NG2_PAUSE){
            *selected=NG2_PROFILE_RASTER_PAUSE;*chosen=*pv;
            if(!pv->restart_ui_observed)scene->restart_label=0;
            return 0;
        }
    }
    if(ng2_analyze_rgba(floor_rgba,PIXELS*4u,896u*4u,scene))return -1;
    if(scene->state!=NG2_FLOOR||!fv->ui_state_observed){unknown_scene(scene);return 0;}
    ng2_profile_restrict_scene(scene,chosen,floor_observed);
    /* Global signatures still lack paired support. Keep motion/input0 and
     * gap31 until their contracts pass; CLEAR is only the explicit local FOV. */
    return 0;
}
