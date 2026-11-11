/* NG-G2: the observed-cell planner and the original 73-candidate, single-input
 * motion verifier. Thresholds and Pillow's two-pass integer blur are preserved.
 * No acknowledgement or planned input count is evidence of displacement.
 */
#include "NG2Core.h"
#include <limits.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define W 224
#define H 104
#define N (W*H)
#define CELLS NG2_TILE_COUNT
#define INF_COST 1000000
static const int ddx[5] = {0,-1,1,0,0};
static const int ddy[5] = {0,0,0,-1,1};
/* Python min(tuple) compares direction names, not DIRECTIONS insertion order. */
static const int lexical[5] = {9,1,2,3,0};

static int index_of(int x,int y) {
    return x < -11 || x > 11 || y < -5 || y > 4 ? -1 : (y+5)*23+x+11;
}
static int px(int i) { return i%23-11; }
static int py(int i) { return i/23-5; }
static int tile(const NG2Scene *s,int x,int y) {
    int i=index_of(x,y); return i<0 ? NG2_TILE_UNKNOWN : s->tiles[i];
}
static int protected_at(const NG2Scene *s,int x,int y) {
    int i=index_of(x,y); return i>=0 && s->protected_cells[i]!=0;
}
static int valid_scene(const NG2Scene *s) {
    int i;
    if (!s || s->abi_version!=NG2_ABI_VERSION || s->struct_size!=sizeof(*s)
        || s->state!=NG2_FLOOR || s->goods<NG2_GOODS_UNKNOWN || s->goods>NG2_GOODS_VISIBLE) return 0;
    for (i=0;i<CELLS;++i)
        if (s->tiles[i]>NG2_TILE_ITEM || s->protected_cells[i]>1) return 0;
    return 1;
}
/* Returns the normal to the observed gold bracket. A vertical bracket wins
 * when both orientations exist, exactly as _gates' second assignment does. */
static int gate(const NG2Scene *s,int x,int y) {
    int k=tile(s,x,y),normal=0;
    if (k!=NG2_TILE_FLOOR && k!=NG2_TILE_DIRT && k!=NG2_TILE_STONE && k!=NG2_TILE_DOOR) return 0;
    if (tile(s,x-1,y)==NG2_TILE_GOLD && tile(s,x+1,y)==NG2_TILE_GOLD) normal=NG2_DOWN;
    if (tile(s,x,y-1)==NG2_TILE_GOLD && tile(s,x,y+1)==NG2_TILE_GOLD) normal=NG2_RIGHT;
    return normal;
}
static int gold_count(const NG2Scene *s) {
    int i,n=0; for (i=0;i<CELLS;++i) n+=s->tiles[i]==NG2_TILE_GOLD; return n;
}
typedef struct { int cost,length,first,order,done; } Path;
static int passage_clear(const NG2Scene *s,int x,int y) {
    int d;
    for (d=0;d<=4;++d)
        if (protected_at(s,x+ddx[d],y+ddy[d])) return 0;
    return 1;
}
static void path_search(const NG2Scene *s,int weighted,int clear_neighbours,Path out[CELLS]) {
    int i,serial=0,origin=index_of(0,0);
    for (i=0;i<CELLS;++i) { out[i].cost=INF_COST;out[i].length=0;out[i].first=0;out[i].order=INT_MAX;out[i].done=0; }
    out[origin].cost=0;out[origin].order=serial++;
    for (;;) {
        int best=-1,d;
        for (i=0;i<CELLS;++i)
            if (!out[i].done && out[i].cost<INF_COST &&
                (best<0 || out[i].cost<out[best].cost ||
                 (out[i].cost==out[best].cost && out[i].order<out[best].order))) best=i;
        if (best<0) break;
        out[best].done=1;
        for (d=1;d<=4;++d) {
            int x=px(best)+ddx[d],y=py(best)+ddy[d],next=index_of(x,y),k,total;
            if (next<0 || protected_at(s,x,y) ||
                (clear_neighbours && !passage_clear(s,x,y))) continue;
            k=tile(s,x,y);
            if (k!=NG2_TILE_FLOOR && !(weighted && k==NG2_TILE_DIRT)) continue;
            total=out[best].cost+(k==NG2_TILE_DIRT ? 2 : 1);
            if (total<out[next].cost) {
                out[next].cost=total;out[next].length=out[best].length+1;
                out[next].first=out[best].first ? out[best].first : d;
                out[next].order=serial++;
            }
        }
    }
}
static void paths(const NG2Scene *s,int weighted,Path out[CELLS]) {
    path_search(s,weighted,0,out);
}
static int lexpoint(int x,int y,int bx,int by) { return x<bx || (x==bx && y<by); }
static void decision(NG2Decision *out,int direction,int reason,int x,int y,const NG2Scene *s) {
    out->direction=direction;out->reason=reason;out->target_x=x;out->target_y=y;
    out->obstacle=direction ? tile(s,ddx[direction],ddy[direction]) : 0;
}
int ng2_choose(const NG2Scene *source,int32_t x,int32_t y,const uint16_t *visits,
               size_t count,const NG2Entrance *entrance,NG2Decision *out) {
    NG2Scene copy;
    const NG2Scene *s=source;
    Path route[CELLS];
    int i,d,passed=-1,best=-1,bestdir=0,bestcost=INF_COST,gx=0,gy=0,nearest=INF_COST,axis;
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!valid_scene(s) || !visits || count!=NG2_VISIT_COUNT || x < -16 || x > 16 || y < -16 || y > 16) return 0;
    if (s->goods==NG2_GOODS_VISIBLE) { out->reason=1;return 0; }
    for (d=0;d<=4;++d)
        if (protected_at(s,ddx[d],ddy[d]) && (!d || tile(s,ddx[d],ddy[d])!=NG2_TILE_GOLD)) {
            out->reason=2;return 0;
        }
    /* Below-grid evidence is not a GOLD cell or an unseen passage. It may
     * select only the observed DOWN floor at the initial position. Actual
     * displacement must reveal ordinary gold before another such choice. */
    if (!gold_count(s) && s->gold_state==NG2_GOLD_EDGE_DOWN) {
        if (s->goods!=NG2_GOODS_UNKNOWN || x || y || (entrance && entrance->valid)
            ||tile(s,0,0)!=NG2_TILE_FLOOR || tile(s,0,1)!=NG2_TILE_FLOOR) {
            out->reason=3;return 0;
        }
        for (i=0;i<CELLS;++i) if (s->protected_cells[i]) {out->reason=2;return 0;}
        decision(out,NG2_DOWN,9,0,1,s);return 1;
    }
    if (!gold_count(s) || tile(s,0,0)!=NG2_TILE_FLOOR) { out->reason=3;return 0; }
    if (entrance && entrance->valid) {
        int64_t rx=(int64_t)entrance->x-x,ry=(int64_t)entrance->y-y;
        d=entrance->direction;
        if (entrance->valid!=1 || d<1 || d>4 || entrance->x < -16 || entrance->x > 16 || entrance->y < -16 || entrance->y > 16 ||
            rx*ddx[d]+ry*ddy[d]>0) { out->reason=4;return 0; }
        passed=(rx>=-11 && rx<=11 && ry>=-5 && ry<=4) ? index_of((int)rx,(int)ry) : -1;
        copy=*source;s=&copy;
        for (i=0;i<CELLS;++i)
            if (copy.tiles[i]!=NG2_TILE_GOLD && px(i)*ddx[d]+py(i)*ddy[d]<0) copy.tiles[i]=NG2_TILE_UNKNOWN;
    }
    paths(s,1,route);
    /* scan() inserts origin first, then the rest in row-major order. */
    for (i=-1;i<CELLS;++i) {
        int p=i<0 ? index_of(0,0) : i,normal,side;
        if (i==index_of(0,0) || p==passed || s->protected_cells[p]) continue;
        normal=gate(s,px(p),py(p));
        if (!normal) continue;
        for (side=1;side>=-1;side-=2) {
            int nx=px(p)+side*ddx[normal],ny=py(p)+side*ddy[normal],n=index_of(nx,ny);
            if (n<0 || route[n].cost==INF_COST) continue;
            if (!route[n].length) {
                for (d=1;d<=4;++d) if (nx+ddx[d]==px(p) && ny+ddy[d]==py(p)) {
                    decision(out,d,5,px(p),py(p),s);return 1;
                }
            } else {
                int first=route[n].first;
                if (best<0 || route[n].cost<bestcost ||
                    (route[n].cost==bestcost && (lexical[first]<lexical[bestdir] ||
                     (first==bestdir && lexpoint(nx,ny,px(best),py(best)))))) {
                    best=n;bestdir=first;bestcost=route[n].cost;
                }
            }
        }
    }
    if (best>=0) { decision(out,bestdir,tile(s,ddx[bestdir],ddy[bestdir])==NG2_TILE_DIRT ? 6 : 7,px(best),py(best),s);return 1; }
    for (i=0;i<CELLS;++i) if (s->tiles[i]==NG2_TILE_GOLD) {
        int gap=abs(px(i))+abs(py(i));
        if (gap<nearest || (gap==nearest && lexpoint(px(i),py(i),gx,gy))) { nearest=gap;gx=px(i);gy=py(i); }
    }
    axis=abs(gy)>=abs(gx);
    paths(s,0,route);bestcost=INF_COST;
    for (i=0;i<CELLS;++i) {
        int k,gap=INF_COST,seen=0,wx=x+px(i),wy=y+py(i),score,axial,bestaxial;
        if (!route[i].length || route[i].cost==INF_COST || i==passed) continue;
        for (k=0;k<CELLS;++k) if (s->tiles[k]==NG2_TILE_GOLD) {
            int distance=abs(px(i)-px(k))+abs(py(i)-py(k)); if (distance<gap) gap=distance;
        }
        if (wx>=-16 && wx<=16 && wy>=-16 && wy<=16) seen=visits[(wy+16)*33+wx+16];
        score=3*gap+route[i].length+4*seen;
        axial=axis ? abs(py(i)-gy) : abs(px(i)-gx);
        bestaxial=best<0 ? INF_COST : (axis ? abs(py(best)-gy) : abs(px(best)-gx));
        d=route[i].first;
        if (best<0 || score<bestcost || (score==bestcost && (axial<bestaxial ||
            (axial==bestaxial && (lexical[d]<lexical[bestdir] ||
             (d==bestdir && lexpoint(px(i),py(i),px(best),py(best)))))))) {
            best=i;bestdir=d;bestcost=score;
        }
    }
    if (best>=0) { decision(out,bestdir,8,px(best),py(best),s);return 1; }
    return 0;
}

static int passage_scene(const NG2Scene *s) {
    return valid_scene(s) && s->gold_state==NG2_GOLD_CLEAR &&
        s->goods==NG2_GOODS_UNKNOWN && !gold_count(s) &&
        tile(s,0,0)==NG2_TILE_FLOOR && passage_clear(s,0,0);
}
static int passage_wall(const NG2Scene *s,int x,int y) {
    int k=tile(s,x,y);
    return k==NG2_TILE_DIRT || k==NG2_TILE_STONE;
}
uint32_t ng2_passage_candidates(const NG2Scene *s) {
    Path route[CELLS];uint32_t result=0;int side,k;
    if (!passage_scene(s)) return 0;
    path_search(s,0,1,route);
    for (side=0;side<2;++side) for (k=-2;k<=2;++k) {
        int mx=side ? -3 : k,my=side ? k : -3,dx=side ? -1 : 0,dy=side ? 0 : -1;
        int inboard=index_of(mx-dx,my-dy),mouth=tile(s,mx,my);
        int first=passage_wall(s,mx+dy,my-dx),second=passage_wall(s,mx-dy,my+dx),walls=0,j;
        if (inboard<0 || route[inboard].cost==INF_COST ||
            !passage_clear(s,mx,my) || !passage_clear(s,mx+dx,my+dy)) continue;
        if (mouth==NG2_TILE_FLOOR) {
            if (!first || !second) continue;
        } else if (mouth==NG2_TILE_UNKNOWN) {
            if ((!first && !second) || tile(s,mx+dx,my+dy)!=NG2_TILE_FLOOR) continue;
            for (j=-3;j<=3;++j) walls+=passage_wall(s,side ? -3 : j,side ? j : -3);
            if (walls<3) continue;
        } else continue;
        result|=UINT32_C(1)<<(side*5+k+2);
    }
    return result;
}
int ng2_choose_passage(const NG2Scene *s,int32_t x,int32_t y,
                       int32_t mouth_x,int32_t mouth_y,NG2Decision *out) {
    Path route[CELLS];int dx,dy,gx,gy,origin_gap,i,best=-1,best_gap=INF_COST;
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!passage_scene(s) || x < -16 || x > 16 || y < -16 || y > 16) return 0;
    if (mouth_y==-3 && mouth_x>=-2 && mouth_x<=2) {dx=0;dy=-1;}
    else if (mouth_x==-3 && mouth_y>=-2 && mouth_y<=2) {dx=-1;dy=0;}
    else return 0;
    /* The caller retains the initially detected world mouth. Re-running the
     * initial-room detector at a moved camera would invent another origin. */
    gx=mouth_x+dx-x;gy=mouth_y+dy-y;origin_gap=abs(gx)+abs(gy);
    if (!origin_gap) return 0;
    path_search(s,0,1,route);
    for (i=0;i<CELLS;++i) {
        int gap=abs(px(i)-gx)+abs(py(i)-gy),d=route[i].first;
        if (!route[i].length || route[i].cost==INF_COST || gap>=origin_gap) continue;
        if (best<0 || gap<best_gap || (gap==best_gap &&
            (route[i].length<route[best].length || (route[i].length==route[best].length &&
             (lexical[d]<lexical[route[best].first] ||
              (d==route[best].first && lexpoint(px(i),py(i),px(best),py(best)))))))) {
            best=i;best_gap=gap;
        }
    }
    if (best<0) return 0;
    decision(out,route[best].first,10,px(best),py(best),s);
    return route[best].length;
}

typedef struct { unsigned char normalized[N],texture[N],positive[N],detail[N],blur[N]; } View;
typedef struct { double score;int sx,sy; } Candidate;
static int clamp(int v,int high) { return v<0 ? 0 : (v>=high ? high-1 : v); }
static void view(const unsigned char raw[N],View *out) {
    unsigned char horizontal[N];
    int x,y;
    for (y=0;y<H;++y) for (x=0;x<W;++x)
        horizontal[y*W+x]=(unsigned char)((raw[y*W+clamp(x-1,W)]+raw[y*W+x]+raw[y*W+clamp(x+1,W)]+1)/3);
    for (y=0;y<H;++y) for (x=0;x<W;++x) {
        int at=y*W+x,values[9],a,b,n=0,blur,detail,median;
        for (a=-1;a<=1;++a) for (b=-1;b<=1;++b) values[n++]=raw[clamp(y+a,H)*W+clamp(x+b,W)];
        for (a=1;a<9;++a) { int v=values[a];b=a;while (b>0 && values[b-1]>v) {values[b]=values[b-1];--b;}values[b]=v; }
        median=values[4];blur=(horizontal[clamp(y-1,H)*W+x]+horizontal[at]+horizontal[clamp(y+1,H)*W+x]+1)/3;
        out->blur[at]=(unsigned char)blur;
        detail=(int)raw[at]-blur+128;
        out->normalized[at]=raw[at]<=6 ? 0 : (unsigned char)(detail<0 ? 0 : (detail>255 ? 255 : detail));
        out->texture[at]=(unsigned char)(raw[at]>6 && abs((int)raw[at]-median)>=3);
        out->positive[at]=(unsigned char)((int)raw[at]-median>=3);
        out->detail[at]=(unsigned char)(raw[at]>6 && abs((int)raw[at]-median)>=6);
    }
}
static int mask(int x,int y,int expanded) {
    if (x<40 || x>=179 || y<20 || y>=79) return 0;
    if (!expanded) return !(x>=90 && x<139 && y>=36);
    return !(x>=103 && x<122 && y>=43 && y<61) && !(x>=115 && x<154 && y>=38 && y<80);
}
static unsigned char even_round(double v) {
    unsigned int n=(unsigned int)v;double f=v-n;
    if (f>.5 || (f==.5 && (n&1u))) ++n;
    return (unsigned char)(n>255 ? 255 : n);
}
static double intensity(const View *a,const View *b,int sx,int sy) {
    uint32_t count=0,sa=0,sb=0,qa=0,qb=0,total=0;
    int x,y;double contrast,ma,mb,gain;unsigned char lut[256];
    for (y=20;y<79;++y) for (x=40;x<179;++x) {
        unsigned int av,bv;
        if (!mask(x,y,0) || !mask(x+sx,y+sy,0)) continue;
        av=a->normalized[y*W+x];bv=b->normalized[(y+sy)*W+x+sx];
        if (av<=6 || bv<=6) continue;
        ++count;sa+=av;sb+=bv;qa+=av*av;qb+=bv*bv;
    }
    if (count<300) return INFINITY;
    contrast=(sqrt(((double)qa-(double)sa*sa/count)/count)+sqrt(((double)qb-(double)sb*sb/count)/count))/2;
    ma=(double)sa/count;mb=(double)sb/count;
    if (contrast<2.5 || ma<6 || mb<6) return INFINITY;
    gain=ma/mb;if (gain<.65) gain=.65;else if (gain>1.55) gain=1.55;
    for (x=0;x<256;++x) { volatile double product=(double)x*gain;lut[x]=even_round(product); }
    for (y=20;y<79;++y) for (x=40;x<179;++x) {
        int av,bv;
        if (!mask(x,y,0) || !mask(x+sx,y+sy,0)) continue;
        av=a->normalized[y*W+x];bv=b->normalized[(y+sy)*W+x+sx];
        if (av>6 && bv>6) total+=(uint32_t)abs(av-(int)lut[bv]);
    }
    return (double)total/count/contrast;
}
static int ranked(const void *left,const void *right) {
    const Candidate *a=(const Candidate *)left,*b=(const Candidate *)right;
    if (a->score<b->score) return -1;
    if (a->score>b->score) return 1;
    return a->sx!=b->sx ? (a->sx<b->sx ? -1 : 1) : (a->sy<b->sy ? -1 : a->sy>b->sy);
}
static void texture_match(const View *a,const View *b,int sx,int sy,int expanded,int *support,int *bad,int regions[3]) {
    int x,y;*support=0;*bad=0;
    if (regions) regions[0]=regions[1]=regions[2]=0;
    for (y=20;y<79;++y) for (x=40;x<179;++x) {
        int old=y*W+x,other;
        if (!mask(x,y,expanded) || !mask(x+sx,y+sy,expanded)) continue;
        other=(y+sy)*W+x+sx;
        if (!a->texture[old] || !b->texture[other]) continue;
        ++*support;*bad+=a->positive[old]!=b->positive[other];
        if (regions) {
            if (y<36) ++regions[0];
            else if (x<90) ++regions[1];
            else if (x>=139) ++regions[2];
        }
    }
}
static int translated_gold(const NG2Scene *a,const NG2Scene *b,int tx,int ty,int exact) {
    int i,ac=gold_count(a),bc=gold_count(b);
    if (exact && ac!=bc) return 0;
    for (i=0;i<CELLS;++i) if (a->tiles[i]==NG2_TILE_GOLD && tile(b,px(i)+tx,py(i)+ty)!=NG2_TILE_GOLD) return 0;
    return 1;
}
static int closed_translation(const NG2Scene *a,const NG2Scene *b,int sx,int sy) {
    int i,tx=sx/9,ty=sy/9;
    if ((sx==0 && sy==0) || sx%9 || sy%9 || gold_count(a)<2 || !translated_gold(a,b,tx,ty,1)) return 0;
    for (i=0;i<CELLS;++i)
        if (a->tiles[i]==NG2_TILE_DOOR && gate(a,px(i),py(i)) &&
            tile(b,px(i)+tx,py(i)+ty)==NG2_TILE_DOOR && gate(b,px(i)+tx,py(i)+ty)) return 1;
    return 0;
}
static int partial_match(const NG2Scene *a,const NG2Scene *b,int tx,int ty) {
    int i,j,gx=0,gy=0,anchors[CELLS],n=0;
    for (i=0;i<CELLS;++i) if (a->tiles[i]==NG2_TILE_GOLD) {gx=px(i);gy=py(i);}
    if (tile(b,gx+tx,gy+ty)!=NG2_TILE_GOLD) return 0;
    for (i=0;i<CELLS;++i) {
        if (a->tiles[i]==NG2_TILE_STONE) {
            int k=tile(b,px(i)+tx,py(i)+ty);
            if (k!=NG2_TILE_STONE && k!=NG2_TILE_UNKNOWN) return 0;
            if (k==NG2_TILE_STONE) anchors[n++]=i;
        }
        if (b->tiles[i]==NG2_TILE_STONE) {
            int k=tile(a,px(i)-tx,py(i)-ty);
            if (k!=NG2_TILE_STONE && k!=NG2_TILE_UNKNOWN) return 0;
        }
    }
    for (i=0;i<n;++i) for (j=i+1;j<n;++j)
        if ((px(anchors[i])-gx)*(py(anchors[j])-gy)!=(py(anchors[i])-gy)*(px(anchors[j])-gx)) return 1;
    return 0;
}
static int partial_translation(const NG2Scene *a,const NG2Scene *b,int sx,int sy) {
    int amount,d,n=0,tx=0,ty=0;
    if (abs(sx)+abs(sy)!=9 || (sx!=0 && sy!=0) || gold_count(a)!=1 || gold_count(b)<=1) return 0;
    if (partial_match(a,b,0,0)) ++n;
    for (amount=1;amount<=2;++amount) for (d=1;d<=4;++d)
        if (partial_match(a,b,amount*ddx[d],amount*ddy[d])) {++n;tx=amount*ddx[d];ty=amount*ddy[d];}
    return n==1 && tx==sx/9 && ty==sy/9;
}
static int unique_gate_translation(const NG2Scene *a,const NG2Scene *b,int sx,int sy) {
    int amount,d,matches=0,tx=0,ty=0;
    if (gold_count(a)<2) return 0;
    for (amount=0;amount<=2;++amount) for (d=1;d<=(amount ? 4 : 1);++d) {
        int x=amount*ddx[d],y=amount*ddy[d],i;
        if (!translated_gold(a,b,x,y,0)) continue;
        for (i=0;i<CELLS;++i) {
            int ak=a->tiles[i],bk=tile(b,px(i)+x,py(i)+y);
            if (gate(a,px(i),py(i)) && gate(b,px(i)+x,py(i)+y) &&
                ((ak==NG2_TILE_DOOR && (bk==NG2_TILE_DOOR || bk==NG2_TILE_FLOOR)) ||
                 (ak==NG2_TILE_FLOOR && bk==NG2_TILE_FLOOR))) {++matches;tx=x;ty=y;break;}
        }
    }
    return matches==1 && sx==tx*9 && sy==ty*9;
}
static int texture_strength(int support,int opposite,int required_percent) {
    return support>=300 && (required_percent==95 ? 20 : 4)*opposite<=support;
}
static int texture_lead(int support,int opposite,int count,int bad) {
    return count<300 || 20*((int64_t)bad*support-(int64_t)opposite*count)>=3*(int64_t)count*support;
}
static int strong_texture(const View *a,const View *b,const Candidate c[73],int expanded,int require_regions) {
    int support,bad,regions[3],k;
    texture_match(a,b,c[0].sx,c[0].sy,expanded,&support,&bad,regions);
    if (!texture_strength(support,bad,95)) return 0;
    if (require_regions && (int)(regions[0]>=100)+(int)(regions[1]>=100)+(int)(regions[2]>=100)<2) return 0;
    for (k=1;k<73;++k) {
        int count,opposite;
        texture_match(a,b,c[k].sx,c[k].sy,expanded,&count,&opposite,NULL);
        if (!texture_lead(support,bad,count,opposite)) return 0;
    }
    return 1;
}
static void evaluate_motion(const NG2Scene *before,const NG2Scene *after,int direction,
                            const View views[2],Candidate candidates[73],NG2Motion *out) {
    int support,bad,sx,sy,amount;
    double best;
    qsort(candidates,73,sizeof(*candidates),ranked);
    best=candidates[0].score;sx=candidates[0].sx;sy=candidates[0].sy;
    if (!isfinite(best) || candidates[1].score-best<.08) return;
    if (best>.45 && !((closed_translation(before,after,sx,sy) || partial_translation(before,after,sx,sy)) &&
                      strong_texture(&views[0],&views[1],candidates,0,1))) return;
    texture_match(&views[0],&views[1],sx,sy,0,&support,&bad,NULL);
    if (support<300) {
        if (best>.45 || !unique_gate_translation(before,after,sx,sy) || !strong_texture(&views[0],&views[1],candidates,1,0)) return;
    } else if (!texture_strength(support,bad,75)) return;
    if (sx==0 && sy==0) {
        int dx=ddx[direction],dy=ddy[direction];
        out->kind=NG2_BLOCKED;
        if (tile(before,dx,dy)==NG2_TILE_DOOR && tile(after,dx,dy)==NG2_TILE_FLOOR && gate(after,dx,dy)) out->kind=NG2_DOOR_OPENED;
        else if (tile(before,dx,dy)==NG2_TILE_DIRT && tile(after,dx,dy)==NG2_TILE_FLOOR &&
                 !protected_at(before,dx,dy) && !protected_at(after,dx,dy)) out->kind=NG2_TERRAIN_OPENED;
    } else if (sx==-9*ddx[direction] && sy==-9*ddy[direction]) {
        out->kind=NG2_MOVED;out->dx=ddx[direction];out->dy=ddy[direction];
    } else {
        out->kind=NG2_UNEXPECTED;
        if (sx%9==0 && sy%9==0) { out->dx=-sx/9;out->dy=-sy/9; }
        for (amount=1;amount<9;++amount)
            if (sx==-amount*ddx[direction] && sy==-amount*ddy[direction]) out->kind=NG2_TWEEN;
    }
}
static void gate_detail_motion(const NG2Scene *before,const NG2Scene *after,int direction,
                               View views[2],const Candidate candidates[73],NG2Motion *out) {
    int i,dx=ddx[direction],dy=ddy[direction];
    if (out->kind!=NG2_MOTION_UNKNOWN || before->state!=NG2_FLOOR || after->state!=NG2_FLOOR ||
        before->goods!=NG2_GOODS_UNKNOWN || after->goods!=NG2_GOODS_UNKNOWN ||
        before->gold_state!=NG2_GOLD_CANDIDATE || after->gold_state!=NG2_GOLD_CANDIDATE ||
        tile(before,0,0)!=NG2_TILE_FLOOR || tile(after,0,0)!=NG2_TILE_FLOOR ||
        tile(before,dx,dy)!=NG2_TILE_FLOOR || tile(after,dx,dy)!=NG2_TILE_FLOOR ||
        !isfinite(candidates[0].score) || candidates[0].score<=.45 ||
        candidates[1].score-candidates[0].score<.08 ||
        candidates[0].sx!=-9*dx || candidates[0].sy!=-9*dy ||
        !closed_translation(before,after,candidates[0].sx,candidates[0].sy) ||
        !unique_gate_translation(before,after,candidates[0].sx,candidates[0].sy)) return;
    for (i=0;i<CELLS;++i) if (before->protected_cells[i] || after->protected_cells[i]) return;
    /* The original classifier and its three evidence planes are unchanged.
     * Only an unresolved, exact closed-gate translation may additionally use
     * stronger terrain detail. Reuse every original support/95%/15pp/region
     * requirement and all 73 original intensity candidates. */
    memcpy(views[0].texture,views[0].detail,N);
    memcpy(views[1].texture,views[1].detail,N);
    if (!strong_texture(&views[0],&views[1],candidates,0,1)) return;
    out->kind=NG2_MOVED;out->dx=dx;out->dy=dy;
}
/* A just-opened narrow passage may expose merchandise while leaving too
 * little terrain inside the ordinary mask. This separate zero-motion proof
 * adds the observed lower terrain strip; it never changes the MOVE mask. */
static int opening_mask(int x,int y) {
    if (x<40 || x>=179 || y<20 || y>=85) return 0;
    return !(x>=103 && x<122 && y>=43 && y<61) &&
           !(x>=115 && x<154 && y>=38 && y<80);
}
static void opening_texture(const View *a,const View *b,int sx,int sy,
                            int *support,int *bad,int regions[2]) {
    int x,y;*support=0;*bad=0;
    if (regions) regions[0]=regions[1]=0;
    for (y=20;y<85;++y) for (x=40;x<179;++x) {
        int old=y*W+x,other;
        if (!opening_mask(x,y) || !opening_mask(x+sx,y+sy)) continue;
        other=(y+sy)*W+x+sx;
        if (!a->detail[old] || !b->detail[other]) continue;
        ++*support;*bad+=a->positive[old]!=b->positive[other];
        if (regions) ++regions[y<65 ? 0 : 1];
    }
}
static void opening_detail_motion(const NG2Scene *before,const NG2Scene *after,int direction,
                                  const View views[2],const Candidate candidates[73],NG2Motion *out) {
    int dx=ddx[direction],dy=ddy[direction],support,bad,regions[2],k;
    if (out->kind!=NG2_MOTION_UNKNOWN || before->state!=NG2_FLOOR || after->state!=NG2_FLOOR ||
        before->goods>NG2_GOODS_PARTIAL || after->goods>NG2_GOODS_PARTIAL ||
        after->goods<before->goods || before->gold_state!=NG2_GOLD_CANDIDATE ||
        after->gold_state!=NG2_GOLD_CANDIDATE ||
        tile(before,0,0)!=NG2_TILE_FLOOR || tile(after,0,0)!=NG2_TILE_FLOOR ||
        tile(before,dx,dy)!=NG2_TILE_DOOR || tile(after,dx,dy)!=NG2_TILE_FLOOR ||
        protected_at(before,0,0) || protected_at(after,0,0) ||
        protected_at(before,dx,dy) || protected_at(after,dx,dy) ||
        !gate(before,dx,dy) || gate(before,dx,dy)!=gate(after,dx,dy) ||
        !isfinite(candidates[0].score) || candidates[0].score>.45 ||
        candidates[1].score-candidates[0].score<.08 ||
        candidates[0].sx || candidates[0].sy || !unique_gate_translation(before,after,0,0)) return;
    opening_texture(&views[0],&views[1],0,0,&support,&bad,regions);
    if (!texture_strength(support,bad,95) || regions[0]<100 || regions[1]<100) return;
    for (k=1;k<73;++k) {
        int count,opposite;
        opening_texture(&views[0],&views[1],candidates[k].sx,candidates[k].sy,&count,&opposite,NULL);
        if (!texture_lead(support,bad,count,opposite)) return;
    }
    out->kind=NG2_DOOR_OPENED;
}
/* An observed clear-floor passage has no gold bracket. Two fully preserved
 * stone anchors plus a non-collinear dirt anchor identify one translation;
 * they never manufacture an unobserved next cell or a motion credit. */
static int observed_terrain_translation(const NG2Scene *a,const NG2Scene *b,int tx,int ty) {
    int i,first=-1,second=-1,ac=0;
    for (i=0;i<CELLS;++i) {
        ac+=a->tiles[i]==NG2_TILE_STONE;
        if (a->tiles[i]!=NG2_TILE_STONE) continue;
        if (tile(b,px(i)+tx,py(i)+ty)!=NG2_TILE_STONE) return 0;
        if (first<0) first=i;else if (second<0) second=i;
    }
    /* Only the old stone set supplies anchors. Newly illuminated stone is
     * allowed, but cannot add evidence or make two translations unique. */
    if (ac<2) return 0;
    for (i=0;i<CELLS;++i) if (a->tiles[i]==NG2_TILE_DIRT &&
        tile(b,px(i)+tx,py(i)+ty)==NG2_TILE_DIRT &&
        (px(second)-px(first))*(py(i)-py(first))!=
        (py(second)-py(first))*(px(i)-px(first))) return 1;
    return 0;
}
static int unique_terrain_translation(const NG2Scene *a,const NG2Scene *b,int sx,int sy) {
    int amount,d,matches=0,tx=0,ty=0;
    for (amount=0;amount<=2;++amount) for (d=1;d<=(amount ? 4 : 1);++d) {
        int x=amount*ddx[d],y=amount*ddy[d];
        if (observed_terrain_translation(a,b,x,y)) {++matches;tx=x;ty=y;}
    }
    return matches==1 && sx==tx*9 && sy==ty*9;
}
static void passage_detail_motion(const NG2Scene *before,const NG2Scene *after,int direction,
                                 View views[2],const Candidate candidates[73],NG2Motion *out) {
    int i,dx=ddx[direction],dy=ddy[direction];
    if (out->kind!=NG2_MOTION_UNKNOWN || before->goods!=NG2_GOODS_UNKNOWN ||
        after->goods!=NG2_GOODS_UNKNOWN || before->gold_state!=NG2_GOLD_CLEAR ||
        after->gold_state!=NG2_GOLD_CLEAR || tile(before,0,0)!=NG2_TILE_FLOOR ||
        tile(after,0,0)!=NG2_TILE_FLOOR || tile(before,dx,dy)!=NG2_TILE_FLOOR ||
        !isfinite(candidates[0].score) ||
        candidates[1].score-candidates[0].score<.08 ||
        candidates[0].sx!=-9*dx || candidates[0].sy!=-9*dy ||
        !unique_terrain_translation(before,after,candidates[0].sx,candidates[0].sy)) return;
    for (i=0;i<CELLS;++i) if (before->protected_cells[i] || after->protected_cells[i] ||
        before->tiles[i]==NG2_TILE_GOLD || after->tiles[i]==NG2_TILE_GOLD ||
        before->tiles[i]==NG2_TILE_ITEM || after->tiles[i]==NG2_TILE_ITEM) return;
    memcpy(views[0].texture,views[0].detail,N);
    memcpy(views[1].texture,views[1].detail,N);
    if (!strong_texture(&views[0],&views[1],candidates,1,1)) return;
    out->kind=NG2_MOVED;out->dx=dx;out->dy=dy;
}
/* This additional opening-only plane uses a central half-gradient with the
 * original six-gray contrast unit. Both frames must select the same stronger
 * axis; compare that axis's sign. It is independent of the median-detail
 * plane, whose score, mask and thresholds remain unchanged. */
static int gradient_pixel_known(const NG2Scene *a,const NG2Scene *b,int x,int y,int sx,int sy) {
    static const int ox[5]={0,-1,1,0,0},oy[5]={0,0,0,-1,1};
    int i;
    if (!opening_mask(x,y) || !opening_mask(x+sx,y+sy) ||
        (x>=101 && x<123 && y>=80) ||
        (x+sx>=101 && x+sx<123 && y+sy>=80)) return 0;
    for (i=0;i<5;++i) {
        /* Nonnegative numerators over this bounded mask implement floor
         * at the original 36px lattice, centered at (448,207) raw pixels. */
        int ax=(4*(x+ox[i])-34)/36-11,ay=(4*(y+oy[i])-9)/36-5;
        int bx=(4*(x+sx+ox[i])-34)/36-11,by=(4*(y+sy+oy[i])-9)/36-5;
        int old=tile(a,ax,ay),latest=tile(b,bx,by);
        if (!old || old!=latest || old==NG2_TILE_DOOR || old==NG2_TILE_ITEM ||
            protected_at(a,ax,ay) || protected_at(b,bx,by)) return 0;
    }
    return 1;
}
static void gradient_texture(const NG2Scene *a,const NG2Scene *b,int sx,int sy,
                             int *support,int *bad,int regions[2]) {
    int x,y;*support=0;*bad=0;
    if (regions) regions[0]=regions[1]=0;
    for (y=20;y<85;++y) for (x=40;x<179;++x) {
        int old=y*W+x,other=(y+sy)*W+x+sx,ah,av,bh,bv,axis,first,second;
        /* A centered derivative must not count the same boundary edge as
         * independent evidence in both terrain bands. */
        if (y==64 || y==65 || y+sy==64 || y+sy==65) continue;
        if (!gradient_pixel_known(a,b,x,y,sx,sy)) continue;
        ah=(int)a->signature[old+1]-a->signature[old-1];
        av=(int)a->signature[old+W]-a->signature[old-W];
        bh=(int)b->signature[other+1]-b->signature[other-1];
        bv=(int)b->signature[other+W]-b->signature[other-W];
        axis=abs(ah)>=abs(av);
        if (axis!=(abs(bh)>=abs(bv))) continue;
        first=axis ? ah : av;second=axis ? bh : bv;
        if (abs(first)<2*6 || abs(second)<2*6) continue;
        ++*support;*bad+=(first>0)!=(second>0);
        if (regions) ++regions[y<65 ? 0 : 1];
    }
}
static void opening_gradient_motion(const NG2Scene *before,const NG2Scene *after,int direction,
                                    const Candidate candidates[73],NG2Motion *out) {
    int dx=ddx[direction],dy=ddy[direction],support,bad,regions[2],k;
    if (out->kind!=NG2_MOTION_UNKNOWN || before->goods>NG2_GOODS_PARTIAL ||
        after->goods>NG2_GOODS_PARTIAL || after->goods<before->goods ||
        before->gold_state!=NG2_GOLD_CANDIDATE || after->gold_state!=NG2_GOLD_CANDIDATE ||
        tile(before,0,0)!=NG2_TILE_FLOOR || tile(after,0,0)!=NG2_TILE_FLOOR ||
        tile(before,dx,dy)!=NG2_TILE_DOOR || tile(after,dx,dy)!=NG2_TILE_FLOOR ||
        protected_at(before,0,0) || protected_at(after,0,0) ||
        protected_at(before,dx,dy) || protected_at(after,dx,dy) ||
        !gate(before,dx,dy) || gate(before,dx,dy)!=gate(after,dx,dy) ||
        !isfinite(candidates[0].score) || candidates[1].score-candidates[0].score<.08 ||
        candidates[0].sx || candidates[0].sy || !unique_gate_translation(before,after,0,0)) return;
    gradient_texture(before,after,0,0,&support,&bad,regions);
    if (!texture_strength(support,bad,95) || regions[0]<100 || regions[1]<100) return;
    for (k=1;k<73;++k) {
        int count,opposite;
        gradient_texture(before,after,candidates[k].sx,candidates[k].sy,&count,&opposite,NULL);
        if (!texture_lead(support,bad,count,opposite)) return;
    }
    out->kind=NG2_DOOR_OPENED;
}
typedef struct { uint16_t materials;unsigned char axis; signed char sign; } GradientFeature;
typedef struct {
    GradientFeature before[N],after[N];
    uint16_t indices[N];int count;
} StaticGradientCache;
static void static_gradient_features(const NG2Scene *s,GradientFeature features[N],
                                     uint16_t *indices,int *count) {
    static const int ox[5]={0,-1,1,0,0},oy[5]={0,0,0,-1,1};
    int x,y;
    for (y=20;y<85;++y) for (x=40;x<179;++x) {
        int at=y*W+x,i,materials=0,ah,av,axis,strong;
        if (!opening_mask(x,y) || (x>=101 && x<123 && y>=80)) continue;
        for (i=0;i<5;++i) {
            int gx=(4*(x+ox[i])-34)/36-11,gy=(4*(y+oy[i])-9)/36-5;
            int kind=tile(s,gx,gy);
            if (!kind || kind==NG2_TILE_DOOR || kind==NG2_TILE_ITEM || protected_at(s,gx,gy)) break;
            materials|=kind<<(3*i);
        }
        if (i!=5) continue;
        ah=(int)s->signature[at+1]-s->signature[at-1];
        av=(int)s->signature[at+W]-s->signature[at-W];
        axis=abs(ah)>=abs(av);strong=axis ? ah : av;
        if (abs(strong)<2*6) continue;
        features[at].materials=(uint16_t)materials;
        features[at].axis=(unsigned char)axis;
        features[at].sign=(signed char)(strong>0 ? 1 : -1);
        if (indices) indices[(*count)++]=(uint16_t)at;
    }
}
static void static_gradient_texture(const StaticGradientCache *cache,int sx,int sy,
                                    int *support,int *bad,int regions[2]) {
    int i;*support=0;*bad=0;
    if (regions) regions[0]=regions[1]=0;
    /* The original five-dependency, central-gradient predicate is factored
     * into per-frame features. Only old strong pixels can support a match;
     * all 73 shifts still compare identical material, axis, sign and bands. */
    for (i=0;i<cache->count;++i) {
        int at=cache->indices[i],y=at/W,other=at+sy*W+sx;
        const GradientFeature *a=&cache->before[at],*b=&cache->after[other];
        if (y==64 || y==65 || y+sy==64 || y+sy==65 ||
            a->materials!=b->materials || a->axis!=b->axis) continue;
        ++*support;*bad+=a->sign!=b->sign;
        if (regions) ++regions[y<65 ? 0 : 1];
    }
}
/* Additional zero-only evidence for an unchanged observed floor. Keep the
 * original raw phase limits; the existing independent gradient plane may
 * replace insufficient median texture, never displacement or an opening. */
static void static_floor_gradient_motion(const NG2Scene *before,const NG2Scene *after,int direction,
                                         const Candidate candidates[73],NG2Motion *out) {
    int dx=ddx[direction],dy=ddy[direction],i,x,y,center,support,bad,regions[2],k,gold=0;
    StaticGradientCache *cache;
    if (out->kind!=NG2_MOTION_UNKNOWN || before->goods!=NG2_GOODS_UNKNOWN ||
        after->goods!=NG2_GOODS_UNKNOWN || before->gold_state!=NG2_GOLD_CANDIDATE ||
        after->gold_state!=NG2_GOLD_CANDIDATE ||
        tile(before,0,0)!=NG2_TILE_FLOOR || tile(after,0,0)!=NG2_TILE_FLOOR ||
        tile(before,dx,dy)!=NG2_TILE_FLOOR || tile(after,dx,dy)!=NG2_TILE_FLOOR ||
        protected_at(before,0,0) || protected_at(after,0,0) ||
        protected_at(before,dx,dy) || protected_at(after,dx,dy) ||
        !isfinite(candidates[0].score) || candidates[0].score>.45 ||
        candidates[1].score-candidates[0].score<.08 ||
        candidates[0].sx || candidates[0].sy) return;
    for (i=0;i<CELLS;++i) {
        if ((before->tiles[i]==NG2_TILE_GOLD)!=(after->tiles[i]==NG2_TILE_GOLD) ||
            before->protected_cells[i]!=after->protected_cells[i] ||
            before->tiles[i]==NG2_TILE_ITEM || after->tiles[i]==NG2_TILE_ITEM) return;
        gold+=before->tiles[i]==NG2_TILE_GOLD;
    }
    if (!gold) return;
    for (center=0;center<2;++center) for (y=-1;y<=1;++y) for (x=-1;x<=1;++x)
        if (tile(before,x+center*dx,y+center*dy)!=tile(after,x+center*dx,y+center*dy)) return;
    cache=(StaticGradientCache *)calloc(1,sizeof(*cache));
    if (!cache) return;
    static_gradient_features(before,cache->before,cache->indices,&cache->count);
    static_gradient_features(after,cache->after,NULL,NULL);
    static_gradient_texture(cache,0,0,&support,&bad,regions);
    if (!texture_strength(support,bad,95) || regions[0]<100 || regions[1]<100) {free(cache);return;}
    for (k=1;k<73;++k) {
        int count,opposite;
        static_gradient_texture(cache,candidates[k].sx,candidates[k].sy,&count,&opposite,NULL);
        if (!texture_lead(support,bad,count,opposite)) {free(cache);return;}
    }
    free(cache);
    out->kind=NG2_BLOCKED;
}

/* A complete old L supplies a two-dimensional observed shape: three floor
 * cells and two perpendicular, three-cell wall arms. New-only corners never
 * supply anchors; an old corner that disappears supplies no match. */
static int supported_corner(const NG2Scene *s,int x,int y,int sx,int sy) {
    int i;
    if (tile(s,x,y)!=NG2_TILE_FLOOR || tile(s,x-sx,y)!=NG2_TILE_FLOOR ||
        tile(s,x,y-sy)!=NG2_TILE_FLOOR) return 0;
    for (i=0;i<3;++i)
        if (!passage_wall(s,x-i*sx,y+sy) || !passage_wall(s,x+sx,y-i*sy)) return 0;
    return 1;
}
static int corner_translation(const NG2Scene *a,const NG2Scene *b,int tx,int ty) {
    int p,sx,sy,i;
    for (p=0;p<CELLS;++p) for (sy=-1;sy<=1;sy+=2) for (sx=-1;sx<=1;sx+=2) {
        int x=px(p),y=py(p),same=1;
        if (!supported_corner(a,x,y,sx,sy) || !supported_corner(b,x+tx,y+ty,sx,sy)) continue;
        for (i=0;i<3;++i)
            if (tile(a,x-i*sx,y+sy)!=tile(b,x-i*sx+tx,y+sy+ty) ||
                tile(a,x+sx,y-i*sy)!=tile(b,x+sx+tx,y-i*sy+ty)) same=0;
        if (same) return 1;
    }
    return 0;
}
static int unique_corner_translation(const NG2Scene *a,const NG2Scene *b,int sx,int sy) {
    int amount,d,matches=0,tx=0,ty=0;
    for (amount=0;amount<=2;++amount) for (d=1;d<=(amount ? 4 : 1);++d) {
        int x=amount*ddx[d],y=amount*ddy[d];
        if (corner_translation(a,b,x,y)) {++matches;tx=x;ty=y;}
    }
    return matches==1 && sx==9*tx && sy==9*ty;
}

/* This mask observes world pixels, including the starting room's lettering.
 * Fixed HUD, player and heart remain excluded. Legacy masks are unchanged. */
static int world_mask(int x,int y) {
    return x>=40 && x<179 && y>=20 && y<85 &&
        !(x>=103 && x<122 && y>=43 && y<61) && !(x>=101 && x<123 && y>=80);
}
static int world_kernel_known(const NG2Scene *a,const NG2Scene *b,int x,int y,int sx,int sy) {
    int ox,oy;
    /* The union of the four 3x3 blur kernels used by a central derivative
     * has 21 dependencies (the four 5x5 corners are unused). Every dependency
     * must be observed in both frames as the same material, outside UI. */
    for (oy=-2;oy<=2;++oy) for (ox=-2;ox<=2;++ox) {
        int ax,ay,bx,by,old,latest;
        if (abs(ox)==2 && abs(oy)==2) continue;
        if (!world_mask(x+ox,y+oy) || !world_mask(x+sx+ox,y+sy+oy)) return 0;
        ax=(4*(x+ox)-34)/36-11;ay=(4*(y+oy)-9)/36-5;
        bx=(4*(x+sx+ox)-34)/36-11;by=(4*(y+sy+oy)-9)/36-5;
        old=tile(a,ax,ay);latest=tile(b,bx,by);
        if (!old || old!=latest || old==NG2_TILE_DOOR || old==NG2_TILE_ITEM ||
            protected_at(a,ax,ay) || protected_at(b,bx,by)) return 0;
    }
    return 1;
}
static void world_blur_texture(const NG2Scene *a,const NG2Scene *b,const View views[2],
                               int sx,int sy,int *support,int *bad,int regions[2]) {
    int x,y;*support=0;*bad=0;
    if (regions) regions[0]=regions[1]=0;
    for (y=20;y<85;++y) for (x=40;x<179;++x) {
        int old=y*W+x,other=(y+sy)*W+x+sx,ah,av,bh,bv,axis,first,second;
        /* Camera-centered upper/lower bands use fixed y=52. Radius-two
         * dependencies cannot overlap across their boundary. */
        if ((y>=50 && y<54) || (y+sy>=50 && y+sy<54) ||
            !world_kernel_known(a,b,x,y,sx,sy)) continue;
        ah=(int)views[0].blur[old+1]-views[0].blur[old-1];
        av=(int)views[0].blur[old+W]-views[0].blur[old-W];
        bh=(int)views[1].blur[other+1]-views[1].blur[other-1];
        bv=(int)views[1].blur[other+W]-views[1].blur[other-W];
        axis=abs(ah)>=abs(av);
        if (axis!=(abs(bh)>=abs(bv))) continue;
        first=axis ? ah : av;second=axis ? bh : bv;
        if (abs(first)<2*6 || abs(second)<2*6) continue;
        ++*support;*bad+=(first>0)!=(second>0);
        if (regions) ++regions[y<52 ? 0 : 1];
    }
}
static int phase_band_mask(int x,int y,int band) {
    int ox,oy;
    if ((band==0 && x>=110) || (band==1 && x<114)) return 0;
    /* Normalized intensity depends on a 3x3 raw neighborhood. Check the
     * entire dependency in both frames, including player/UI exclusions. */
    for (oy=-1;oy<=1;++oy) for (ox=-1;ox<=1;++ox)
        if (!opening_mask(x+ox,y+oy) ||
            (x+ox>=101 && x+ox<123 && y+oy>=80)) return 0;
    return 1;
}
static double phase_band_intensity(const View *a,const View *b,int sx,int sy,int band) {
    uint32_t count=0,sa=0,sb=0,qa=0,qb=0,total=0;
    int x,y;double contrast,ma,mb,gain;unsigned char lut[256];
    /* Preserve intensity()'s score arithmetic and limits. Only its spatial
     * support is restricted to an independent, dependency-safe raw band. */
    for (y=20;y<85;++y) for (x=40;x<179;++x) {
        unsigned int av,bv;
        if (!phase_band_mask(x,y,band) || !phase_band_mask(x+sx,y+sy,band)) continue;
        av=a->normalized[y*W+x];bv=b->normalized[(y+sy)*W+x+sx];
        if (av<=6 || bv<=6) continue;
        ++count;sa+=av;sb+=bv;qa+=av*av;qb+=bv*bv;
    }
    if (count<300) return INFINITY;
    contrast=(sqrt(((double)qa-(double)sa*sa/count)/count)+sqrt(((double)qb-(double)sb*sb/count)/count))/2;
    ma=(double)sa/count;mb=(double)sb/count;
    if (contrast<2.5 || ma<6 || mb<6) return INFINITY;
    gain=ma/mb;if (gain<.65) gain=.65;else if (gain>1.55) gain=1.55;
    for (x=0;x<256;++x) { volatile double product=(double)x*gain;lut[x]=even_round(product); }
    for (y=20;y<85;++y) for (x=40;x<179;++x) {
        int av,bv;
        if (!phase_band_mask(x,y,band) || !phase_band_mask(x+sx,y+sy,band)) continue;
        av=a->normalized[y*W+x];bv=b->normalized[(y+sy)*W+x+sx];
        if (av>6 && bv>6) total+=(uint32_t)abs(av-(int)lut[bv]);
    }
    return (double)total/count/contrast;
}
static int independent_phase(const View views[2],const Candidate candidates[73]) {
    int band,k;
    for (band=0;band<2;++band) {
        double best=phase_band_intensity(&views[0],&views[1],candidates[0].sx,candidates[0].sy,band);
        if (!isfinite(best)) return 0;
        for (k=1;k<73;++k)
            if (phase_band_intensity(&views[0],&views[1],candidates[k].sx,candidates[k].sy,band)-best<.08) return 0;
    }
    return 1;
}
static void corner_blur_motion(const NG2Scene *before,const NG2Scene *after,int direction,
                               const View views[2],const Candidate candidates[73],NG2Motion *out) {
    int i,k,dx=ddx[direction],dy=ddy[direction],support,bad,regions[2];
    if (out->kind!=NG2_MOTION_UNKNOWN || before->goods!=NG2_GOODS_UNKNOWN ||
        after->goods!=NG2_GOODS_UNKNOWN || before->gold_state!=NG2_GOLD_CLEAR ||
        after->gold_state!=NG2_GOLD_CLEAR || tile(before,0,0)!=NG2_TILE_FLOOR ||
        tile(after,0,0)!=NG2_TILE_FLOOR || tile(before,dx,dy)!=NG2_TILE_FLOOR ||
        !isfinite(candidates[0].score) || candidates[1].score-candidates[0].score<.08 ||
        candidates[0].sx!=-9*dx || candidates[0].sy!=-9*dy) return;
    for (i=0;i<CELLS;++i) if (before->protected_cells[i] || after->protected_cells[i] ||
        before->tiles[i]==NG2_TILE_GOLD || after->tiles[i]==NG2_TILE_GOLD ||
        before->tiles[i]==NG2_TILE_ITEM || after->tiles[i]==NG2_TILE_ITEM) return;
    if (!unique_corner_translation(before,after,candidates[0].sx,candidates[0].sy) ||
        !independent_phase(views,candidates)) return;
    world_blur_texture(before,after,views,candidates[0].sx,candidates[0].sy,&support,&bad,regions);
    if (!texture_strength(support,bad,95) || regions[0]<100 || regions[1]<100) return;
    for (k=1;k<73;++k) {
        int count,opposite;
        world_blur_texture(before,after,views,candidates[k].sx,candidates[k].sy,&count,&opposite,NULL);
        if (!texture_lead(support,bad,count,opposite)) return;
    }
    out->kind=NG2_MOVED;out->dx=dx;out->dy=dy;
}

/* A fixed per-frame axis uses only its actual center/endpoints. The old
 * five-dependency maximum-axis and y65 planes remain unchanged. */
typedef struct { uint16_t materials;unsigned char axis; signed char sign; } ClosedGateAxisFeature;
typedef struct {
    ClosedGateAxisFeature before[N],after[N];
    uint16_t indices[N];int count;
} ClosedGateAxisCache;
static int closed_gate_axis_mask(int x,int y) {
    return opening_mask(x,y) && !(x>=101 && x<123 && y>=80);
}
static void closed_gate_axis_features(const NG2Scene *s,ClosedGateAxisFeature features[N],
                                      uint16_t *indices,int *count) {
    int x,y;
    for (y=20;y<85;++y) for (x=40;x<179;++x) {
        int axis;
        /* Freeze the first eligible axis in this frame, before comparing
         * another frame or any displacement candidate. One pixel, one vote. */
        for (axis=1;axis<=2;++axis) {
            int i,materials=0,delta,ox=axis==1,oy=axis==2;
            for (i=0;i<3;++i) {
                int step=i==0 ? 0 : (i==1 ? -1 : 1),xx=x+step*ox,yy=y+step*oy;
                int gx=(4*xx-34)/36-11,gy=(4*yy-9)/36-5,kind=tile(s,gx,gy);
                if (!closed_gate_axis_mask(xx,yy) || !kind || kind==NG2_TILE_DOOR ||
                    kind==NG2_TILE_ITEM || protected_at(s,gx,gy)) break;
                materials|=kind<<(3*i);
            }
            if (i!=3) continue;
            delta=(int)s->signature[(y+oy)*W+x+ox]-s->signature[(y-oy)*W+x-ox];
            if (abs(delta)<2*6) continue;
            features[y*W+x].materials=(uint16_t)materials;
            features[y*W+x].axis=(unsigned char)axis;
            features[y*W+x].sign=(signed char)(delta>0 ? 1 : -1);
            if (indices) indices[(*count)++]=(uint16_t)(y*W+x);
            break;
        }
    }
}
static void closed_gate_axis_texture(const ClosedGateAxisCache *cache,int sx,int sy,
                                     int *support,int *bad,int regions[2]) {
    int i;*support=0;*bad=0;
    if (regions) regions[0]=regions[1]=0;
    for (i=0;i<cache->count;++i) {
        int at=cache->indices[i],y=at/W,other=at+sy*W+sx;
        const ClosedGateAxisFeature *a=&cache->before[at],*b=&cache->after[other];
        /* Radius-one dependencies cannot overlap across camera-center52. */
        if (y==51 || y==52 || y+sy==51 || y+sy==52 ||
            a->axis!=b->axis || a->materials!=b->materials) continue;
        ++*support;*bad+=a->sign!=b->sign;
        if (regions) ++regions[y<52 ? 0 : 1];
    }
}
static int closed_gate_axis_strong(const ClosedGateAxisCache *cache,const Candidate candidates[73]) {
    int support,bad,regions[2],k;
    closed_gate_axis_texture(cache,candidates[0].sx,candidates[0].sy,&support,&bad,regions);
    if (!texture_strength(support,bad,95) || regions[0]<100 || regions[1]<100) return 0;
    for (k=1;k<73;++k) {
        int count,opposite;
        closed_gate_axis_texture(cache,candidates[k].sx,candidates[k].sy,&count,&opposite,NULL);
        if (!texture_lead(support,bad,count,opposite)) return 0;
    }
    return 1;
}
static void closed_gate_axis_motion(const NG2Scene *before,const NG2Scene *after,int direction,
                                    const Candidate candidates[73],NG2Motion *out) {
    int dx=ddx[direction],dy=ddy[direction],normal=dx ? NG2_RIGHT : NG2_DOWN,i;
    ClosedGateAxisCache *cache;
    if (out->kind!=NG2_MOTION_UNKNOWN || before->state!=NG2_FLOOR || after->state!=NG2_FLOOR ||
        before->goods!=NG2_GOODS_UNKNOWN || after->goods!=NG2_GOODS_UNKNOWN ||
        before->gold_state!=NG2_GOLD_CANDIDATE || after->gold_state!=NG2_GOLD_CANDIDATE ||
        tile(before,0,0)!=NG2_TILE_FLOOR || tile(before,dx,dy)!=NG2_TILE_FLOOR ||
        tile(after,0,0)!=NG2_TILE_FLOOR || tile(before,2*dx,2*dy)!=NG2_TILE_DOOR ||
        tile(after,dx,dy)!=NG2_TILE_DOOR || gate(before,2*dx,2*dy)!=normal || gate(after,dx,dy)!=normal ||
        !isfinite(candidates[0].score) || candidates[0].score<=.45 ||
        !(candidates[1].score-candidates[0].score>=.08) ||
        candidates[0].sx!=-9*dx || candidates[0].sy!=-9*dy ||
        !closed_translation(before,after,candidates[0].sx,candidates[0].sy) ||
        !unique_gate_translation(before,after,candidates[0].sx,candidates[0].sy)) return;
    for (i=0;i<CELLS;++i)
        if (before->protected_cells[i] || after->protected_cells[i] ||
            before->tiles[i]==NG2_TILE_ITEM || after->tiles[i]==NG2_TILE_ITEM) return;
    cache=(ClosedGateAxisCache *)calloc(1,sizeof(*cache));
    if (!cache) return;
    closed_gate_axis_features(before,cache->before,cache->indices,&cache->count);
    closed_gate_axis_features(after,cache->after,NULL,NULL);
    if (closed_gate_axis_strong(cache,candidates)) {
        out->kind=NG2_MOVED;out->dx=dx;out->dy=dy;
    }
    free(cache);
}

/* An old singleton may become one leaf of a newly visible closed gate.
 * Only previously UNKNOWN door/opposite-leaf cells establish this new
 * geometry. Surviving old STONE anchors, not new or changed cells, support it. */
static int revealed_gate_match(const NG2Scene *before,const NG2Scene *after,int tx,int ty) {
    int i,j,gx=0,gy=0,door=-1,normal=0,cx,cy,ax,ay,other_x,other_y;
    if (gold_count(before)!=1 || gold_count(after)!=2) return 0;
    for (i=0;i<CELLS;++i) {
        if (before->tiles[i]==NG2_TILE_GOLD) {gx=px(i);gy=py(i);}
        if (after->tiles[i]==NG2_TILE_DOOR && gate(after,px(i),py(i))) {
            if (door>=0) return 0;
            door=i;normal=gate(after,px(i),py(i));
        }
    }
    if (door<0) return 0;
    cx=px(door);cy=py(door);ax=gx+tx;ay=gy+ty;
    if (tile(after,ax,ay)!=NG2_TILE_GOLD) return 0;
    if (normal==NG2_DOWN) {
        if (ay!=cy || abs(ax-cx)!=1) return 0;
    } else if (normal==NG2_RIGHT) {
        if (ax!=cx || abs(ay-cy)!=1) return 0;
    } else return 0;
    other_x=2*cx-ax;other_y=2*cy-ay;
    if (tile(before,cx-tx,cy-ty)!=NG2_TILE_UNKNOWN ||
        tile(before,other_x-tx,other_y-ty)!=NG2_TILE_UNKNOWN) return 0;
    for (i=0;i<CELLS;++i) {
        if (before->tiles[i]!=NG2_TILE_STONE || tile(after,px(i)+tx,py(i)+ty)!=NG2_TILE_STONE) continue;
        for (j=i+1;j<CELLS;++j) {
            if (before->tiles[j]!=NG2_TILE_STONE || tile(after,px(j)+tx,py(j)+ty)!=NG2_TILE_STONE) continue;
            if ((px(i)-gx)*(py(j)-gy)!=(py(i)-gy)*(px(j)-gx)) return 1;
        }
    }
    return 0;
}
static int unique_revealed_gate_translation(const NG2Scene *before,const NG2Scene *after,int sx,int sy) {
    int amount,d,matches=0,tx=0,ty=0;
    /* Each candidate independently tests all old anchor pairs. A different
     * surviving pair cannot hide a second possible camera displacement. */
    for (amount=0;amount<=2;++amount) for (d=1;d<=(amount ? 4 : 1);++d) {
        int x=amount*ddx[d],y=amount*ddy[d];
        if (revealed_gate_match(before,after,x,y)) {++matches;tx=x;ty=y;}
    }
    return matches==1 && sx==9*tx && sy==9*ty;
}
static void revealed_gate_axis_motion(const NG2Scene *before,const NG2Scene *after,int direction,
                                      const Candidate candidates[73],NG2Motion *out) {
    int dx=ddx[direction],dy=ddy[direction],i;
    ClosedGateAxisCache *cache;
    if (out->kind!=NG2_MOTION_UNKNOWN || before->state!=NG2_FLOOR || after->state!=NG2_FLOOR ||
        before->goods!=NG2_GOODS_UNKNOWN || after->goods!=NG2_GOODS_UNKNOWN ||
        before->gold_state!=NG2_GOLD_CANDIDATE || after->gold_state!=NG2_GOLD_CANDIDATE ||
        tile(before,0,0)!=NG2_TILE_FLOOR || tile(before,dx,dy)!=NG2_TILE_FLOOR ||
        tile(after,0,0)!=NG2_TILE_FLOOR || !isfinite(candidates[0].score) || candidates[0].score>.45 ||
        !(candidates[1].score-candidates[0].score>=.08) ||
        candidates[0].sx!=-9*dx || candidates[0].sy!=-9*dy ||
        !unique_revealed_gate_translation(before,after,candidates[0].sx,candidates[0].sy)) return;
    for (i=0;i<CELLS;++i)
        if (before->protected_cells[i] || after->protected_cells[i] ||
            before->tiles[i]==NG2_TILE_ITEM || after->tiles[i]==NG2_TILE_ITEM) return;
    cache=(ClosedGateAxisCache *)calloc(1,sizeof(*cache));
    if (!cache) return;
    closed_gate_axis_features(before,cache->before,cache->indices,&cache->count);
    closed_gate_axis_features(after,cache->after,NULL,NULL);
    if (closed_gate_axis_strong(cache,candidates)) {
        out->kind=NG2_MOVED;out->dx=dx;out->dy=dy;
    }
    free(cache);
}

int ng2_motion(const NG2Scene *before,const NG2Scene *after,int32_t direction,NG2Motion *out) {
    View *views;
    Candidate candidates[73];
    int n=1,amount,d;
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!valid_scene(before) || !valid_scene(after) || direction<1 || direction>4) return 0;
    views=(View *)malloc(2*sizeof(*views));
    if (!views) return 0;
    view(before->signature,&views[0]);view(after->signature,&views[1]);
    candidates[0].sx=0;candidates[0].sy=0;candidates[0].score=intensity(&views[0],&views[1],0,0);
    for (amount=1;amount<=18;++amount) for (d=1;d<=4;++d) {
        candidates[n].sx=amount*ddx[d];candidates[n].sy=amount*ddy[d];
        candidates[n].score=intensity(&views[0],&views[1],candidates[n].sx,candidates[n].sy);++n;
    }
    evaluate_motion(before,after,direction,views,candidates,out);
    gate_detail_motion(before,after,direction,views,candidates,out);
    opening_detail_motion(before,after,direction,views,candidates,out);
    passage_detail_motion(before,after,direction,views,candidates,out);
    opening_gradient_motion(before,after,direction,candidates,out);
    static_floor_gradient_motion(before,after,direction,candidates,out);
    corner_blur_motion(before,after,direction,views,candidates,out);
    closed_gate_axis_motion(before,after,direction,candidates,out);
    revealed_gate_axis_motion(before,after,direction,candidates,out);
    free(views);return 1;
}
int ng2_entered_gate(const NG2Scene *before,const NG2Scene *after,int32_t direction,
                     int32_t x,int32_t y,int32_t motion,NG2Entrance *out) {
    int dx,dy;
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!valid_scene(before) || !valid_scene(after) || direction<1 || direction>4 || x < -16 || x > 16 || y < -16 || y > 16) return 0;
    dx=ddx[direction];dy=ddy[direction];
    if (motion!=NG2_MOVED || tile(before,dx,dy)!=NG2_TILE_FLOOR || tile(after,0,0)!=NG2_TILE_FLOOR ||
        !gate(before,dx,dy) || !gate(after,0,0) || protected_at(before,dx,dy) || protected_at(after,0,0)) return 0;
    if (x+dx < -16 || x+dx > 16 || y+dy < -16 || y+dy > 16) return 0;
    out->valid=1;out->x=x+dx;out->y=y+dy;out->direction=direction;return 1;
}
