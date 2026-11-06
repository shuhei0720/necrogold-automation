/* TEST-018: fixed 896x414 RGB / 23x10 grid / 25x25 cells.
 * Reproducible i386 build (GCC 13.3.0):
 * gcc -m32 -march=i386 -mno-sse -mno-sse2 -O2 -fPIC -ffreestanding \
 *   -fno-stack-protector -fno-builtin -shared -nostdlib -Wl,--build-id=none \
 *   necroprobe/navigation_stats.c -o necroprobe/navigation_stats_i386.so
 * Output: 230 row-major groups of median R,G,B and stddev>=2 flag.
 * No allocation, floating point, dependencies or shared mutable state.
 */
#define RGB_LENGTH (896u * 414u * 3u)
#define OUTPUT_LENGTH (23u * 10u * 4u)
int necro_navigation_stats(const unsigned char *rgb, unsigned int rgb_len,
                           unsigned char *out, unsigned int out_len) {
    unsigned int row, col;
    if (!rgb || !out || rgb_len != RGB_LENGTH || out_len != OUTPUT_LENGTH) return -1;
    for (row=0; row<10; ++row) {
        for (col=0; col<23; ++col) {
            unsigned int hist[3][256];
            unsigned int sums[3]={0,0,0}, squares[3]={0,0,0};
            unsigned int x,y,c,v,spread=0,index=(row*23+col)*4;
            for (c=0;c<3;++c) for (v=0;v<256;++v) hist[c][v]=0;
            for (y=15+36*row;y<40+36*row;++y) {
                const unsigned char *p=rgb+(y*896+40+36*col)*3;
                for (x=0;x<25;++x,p+=3) {
                    for (c=0;c<3;++c) {
                        v=p[c];++hist[c][v];sums[c]+=v;squares[c]+=v*v;
                    }
                }
            }
            for (c=0;c<3;++c) {
                unsigned int count=0;
                for (v=0;v<256;++v) {count+=hist[c][v];if(count>312)break;}
                out[index+c]=(unsigned char)v;
                /* Widen BEFORE multiplication: maximum product is 25,400,390,625.
                 * Population variance >=4 is exactly max(stddev)>=2. No division.
                 */
                if ((unsigned long long)625*squares[c]-(unsigned long long)sums[c]*sums[c]
                    >= (unsigned long long)4*625*625) spread=1;
            }
            out[index+3]=(unsigned char)spread;
        }
    }
    return 0;
}
