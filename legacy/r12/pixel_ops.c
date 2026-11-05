/* Fixed-size image operations for the iSH build. No libc or SIMD dependency. */
enum { W = 597, H = 276, GW = 199, GH = 92 };
typedef unsigned char Byte;
typedef unsigned short Count;
int kernel_abi(void) { return 10; }
static int prefix[H + 1][W + 1];
static Count density[H][W];

static int min_i(int a, int b) { return a < b ? a : b; }
static int max_i(int a, int b) { return a > b ? a : b; }
static double root(double value) {
    double result;
    __asm__("fsqrt" : "=t"(result) : "0"(value));
    return result;
}

/* Integer inequalities implement the calibrated RGB ratios without x87 per pixel. */
static int gold(int r, int g, int b) {
    return r > 52 && 1000*g > 685*r && 100*g < 92*r &&
           100*b < 58*g && 100*b > 7*g;
}
static int sign_colour(int r, int g, int b) {
    return r > 57 && 1000*g > 865*r && 100*g < 105*r && 100*b < 24*g;
}

static int window_counts(const Byte *rgb, int is_sign, int size) {
    int max_count = 0;
    for (int y = 0; y < H; ++y) {
        int row = 0;
        for (int x = 0; x < W; ++x, rgb += 3) {
            if (is_sign) {
                if (!(y < 34 && x >= W-155) && !(y >= 214 && x >= 477))
                    row += sign_colour(rgb[0],rgb[1],rgb[2]);
            } else if (y < 253 && !(y < 36 && x < 95) && !(y < 53 && x >= W-155)
                       && !(y >= 210 && x >= 478) && !(y >= 214 && x >= 270 && x < 323))
                row += gold(rgb[0],rgb[1],rgb[2]);
            prefix[y+1][x+1] = prefix[y][x+1] + row;
        }
    }
    for (int y = 0; y < H; ++y) {
        int top = max_i(0,y-size/2), bottom = min_i(H,y+size-size/2);
        for (int x = 0; x < W; ++x) {
            int left = max_i(0,x-size/2), right = min_i(W,x+size-size/2);
            int count = prefix[bottom][right]-prefix[bottom][left]
                      - prefix[top][right]+prefix[top][left];
            density[y][x] = (Count)count;
            if (count > max_count) max_count = count;
        }
    }
    return max_count;
}

int has_gold(const Byte *rgb) { return window_counts(rgb,0,18)*100 > 53*18*18; }

/* Return two sign centres, one candidate sign, or none. Strict tie handling
   preserves the row-major position and gap chosen during calibration. */
int locate_signs(const Byte *rgb, int *out) {
    int high = window_counts(rgb,1,20), best = -1;
    if (high < 152) return 0;
    for (int gap = 47; gap <= 49; ++gap)
        for (int y = 0; y < H; ++y)
            for (int x = 0; x < W-gap; ++x) {
                int n = min_i(density[y][x],density[y][x+gap]);
                if (n > best) { best = n; out[0] = x; out[1] = y; out[2] = gap; }
            }
    if (best >= 152) return 2;
    if (high >= 172)
        for (int y = 0; y < H; ++y)
            for (int x = 0; x < W; ++x)
                if (density[y][x] == high) { out[0] = x; out[1] = y; return 1; }
    return 0;
}

double ring_match(const Byte *rgb, const Byte *rgba, int w, int h, int cx, int sign_y) {
    /* All reference templates fit within 23 x 20 pixels. */
    int offsets[460], dark[460], colours[460][3], intensity[460];
    int count = 0, n_dark = 0, energy = 0, target_sum = 0, target_sq = 0;
    if (w < 1 || w > 23 || h < 1 || h > 20) return 0;
    for (int y=0; y<h; ++y) for (int x=0; x<w; ++x, rgba+=4) {
        if (rgba[3] < 220) continue;
        int peak=max_i(max_i(rgba[0],rgba[1]),rgba[2]);
        int offset=3*(y*W+x);
        if (peak < 15) dark[n_dark++]=offset;
        if (peak <= 35) continue;
        offsets[count]=offset;
        int sum=0;
        for(int c=0;c<3;++c) {
            int t=rgba[c];
            colours[count][c]=t; sum+=t; energy+=t*t;
        }
        intensity[count++]=sum; target_sum+=sum; target_sq+=sum*sum;
    }
    if (!count || !n_dark || !energy) return 0;
    double target_var=target_sq-(double)target_sum*target_sum/count, best=0;
    for (int y=max_i(0,sign_y+16);y<=min_i(H-h,sign_y+38);++y)
        for (int x=max_i(0,cx-w/2-5);x<=min_i(W-w,cx-w/2+5);++x) {
            const Byte *patch=rgb+3*(y*W+x);
            int dot=0,sum=0,sq=0,cross=0;
            for (int i=0;i<count;++i) {
                const Byte *p=patch+offsets[i];
                int v=p[0]+p[1]+p[2]; sum+=v; sq+=v*v; cross+=v*intensity[i];
                for(int c=0;c<3;++c) dot+=p[c]*colours[i][c];
            }
            double gain=(double)dot/energy;
            if(gain<.37) gain=.37;
            if(gain>1.30) gain=1.30;
            int matches=0, outline=0;
            for(int i=0;i<count;++i) {
                const Byte *p=patch+offsets[i]; double error=0;
                for(int c=0;c<3;++c) {
                    double diff=p[c]-gain*colours[i][c]; error+=diff<0 ? -diff : diff;
                }
                matches+=error<3*(13+15*gain);
            }
            for(int i=0;i<n_dark;++i) {
                const Byte *p=patch+dark[i]; outline+=p[0]+p[1]+p[2]<144;
            }
            double var=sq-(double)sum*sum/count;
            double norm=root(var>0 ? var*target_var : 0);
            /* Both intensity vectors are RGB sums; original means divide by 3. */
            double shape=(cross-(double)sum*target_sum/count)/(norm>9 ? norm : 9);
            if(shape<0) shape=0;
            double q=(.55*matches/count+.45*shape)*(.80+.20*outline/n_dark);
            if(q>best) best=q;
        }
    return best;
}

/* A gradient uses the sum of the three channels, so the amplitude threshold
   is 15, equivalent to 5 on the RGB mean. */
typedef struct { short dx,dy; float magnitude; } Gradient;
int gradient_bytes(void) { return GW*GH*(int)sizeof(Gradient); }
static int luminance(const Byte *p) { return p[0]+p[1]+p[2]; }
void gradients(const Byte *rgb, Gradient *out) {
    for(int y=0;y<GH;++y) for(int x=0;x<GW;++x,++out) {
        const Byte *p=rgb+3*(3*y*W+3*x);
        int base=luminance(p);
        int gx=x+1<GW ? luminance(p+9)-base : 0;
        int gy=y+1<GH ? luminance(p+9*W)-base : 0;
        out->dx=gx; out->dy=gy;
        int squared=gx*gx+gy*gy;
        out->magnitude=squared>225 ? (float)root(squared) : 0;
    }
}
static double similarity(const Gradient *old, const Gradient *cur, int dx, int dy) {
    double total=0; int both=0,either=0;
    for(int y=16;y<70;++y) for(int x=40;x<160;++x) {
        if(x+dx<0 || x+dx>=GW || y+dy<0 || y+dy>=GH) continue;
        const Gradient *a=old+(y+dy)*GW+x+dx,*b=cur+y*GW+x;
        if(a->magnitude || b->magnitude) ++either;
        if(a->magnitude && b->magnitude) {
            ++both;
            int dot=a->dx*b->dx+a->dy*b->dy;
            if(dot>0) total+=dot/((double)a->magnitude*b->magnitude);
        }
    }
    return both>=26 ? total/either : 0;
}
static double best_similarity(const Gradient *old,const Gradient *cur,int dx,int dy) {
    const int offsets[5][2]={{0,0},{-1,0},{1,0},{0,-1},{0,1}};
    double best=0;
    for(int i=0;i<5;++i) {
        double score=similarity(old,cur,dx+offsets[i][0],dy+offsets[i][1]);
        if(score>best) best=score;
    }
    return best;
}
int observed_move(const Gradient *old,const Gradient *cur,int dx,int dy) {
    if(dx*dx+dy*dy!=1) return -1;
    double still=best_similarity(old,cur,0,0), moved=best_similarity(old,cur,8*dx,8*dy);
    if(moved>.22 && moved>still+.065) return 1;
    if(still>.22 && still>moved+.065) return 0;
    return -1;
}

/* Verify the actual displacement of a short straight run, including zero or
   partial movement. Never assume every requested tap moved the character. */
int observed_count(const Gradient *old,const Gradient *cur,int dx,int dy,int maximum) {
    if(dx*dx+dy*dy!=1 || maximum<1 || maximum>3) return -1;
    double best=0,second=0; int index=-1;
    for(int n=0;n<=maximum;++n) {
        double score=best_similarity(old,cur,8*n*dx,8*n*dy);
        if(score>best) {second=best;best=score;index=n;}
        else if(score>second) second=score;
    }
    return best>.22 && best>second+.065 ? index : -1;
}

int hud_banner(const Byte *rgb) {
    int bright=0,grey=0,n=239*41;
    for(int y=51;y<92;++y) for(int x=179;x<418;++x) {
        const Byte *p=rgb+3*(y*W+x);
        int low=min_i(p[0],min_i(p[1],p[2])),high=max_i(p[0],max_i(p[1],p[2]));
        int sum=p[0]+p[1]+p[2];
        bright+=low>170;grey+=high-low<16 && sum>51 && sum<189;
    }
    return bright*1000>45*n && grey*100>48*n;
}

/* Same 81 samples/median rules as navigation.scan, without per-pixel Python. */
void scan_tiles(const Byte *rgb,int *out) {
    for(int j=-5;j<=4;++j) for(int i=-11;i<=11;++i) {
        int k=(j+5)*23+i+11,x=298+24*i,y=138+24*j;
        out[k]=0;
        if((x<94 && y<93) || (x>448 && y<53) || (x>478 && y>204) ||
           (i>-2 && i<2 && y>222)) continue;
        if(i==0 && j==0) {out[k]=1;continue;}
        int hist[3][256],golds=0;
        for(int c=0;c<3;++c) for(int v=0;v<256;++v) hist[c][v]=0;
        for(int yy=y-8;yy<=y+8;yy+=2) for(int xx=x-8;xx<=x+8;xx+=2) {
            const Byte *p=rgb+3*(yy*W+xx);
            for(int c=0;c<3;++c) ++hist[c][p[c]];
            golds+=gold(p[0],p[1],p[2]);
        }
        if(golds>=42) {out[k]=4;continue;}
        int median[3];
        for(int c=0;c<3;++c) {
            int count=0;
            for(int v=0;v<256;++v) if((count+=hist[c][v])>40) {median[c]=v;break;}
        }
        int r=median[0],g=median[1],b=median[2];
        if(r<10 && g<10) continue;
        /* Exact rational thresholds: x87 extended precision and SSE double
           must classify the same RGB bytes identically at the boundary. */
        if(100*b>53*r && 100*g>69*r && r>45) out[k]=3;
        else if(100*b<55*r && 100*g>42*r) out[k]=2;
        else out[k]=1;
    }
}
