/* One bounded stdin packet; one bounded raw-score JSON reply. No local files. */
#include "ring.h"
#include "feature_sha.h"
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <fenv.h>

static unsigned char filtered[RING_FILTERED],rgba[RING_RGBA];
static RingObservation observation;
static char reply[8192];
static size_t used;
static uint32_t little32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int append(const char *format,...){
    va_list args;va_start(args,format);
    int count=vsnprintf(reply+used,sizeof(reply)-used,format,args);
    va_end(args);
    if(count<0||(size_t)count>=sizeof(reply)-used)return -1;
    used+=(size_t)count;return 0;
}
static int fail(void){fputs("ring_native_invalid\n",stderr);return 2;}
static int same_feature(const unsigned char *bytes){
    static const char hex[]="0123456789abcdef";
    for(int i=0;i<32;i++)if(hex[bytes[i]>>4]!=FIXED_FEATURE_SHA256[i*2]||hex[bytes[i]&15]!=FIXED_FEATURE_SHA256[i*2+1])return 0;
    return 1;
}
int main(void){
    unsigned char header[80],extra;
    if(fegetround()!=FE_TONEAREST)return fail();
    if(fread(header,1,sizeof(header),stdin)!=sizeof(header)||memcmp(header,"NG2RING1",8))return fail();
    uint32_t mode=little32(header+8),length=little32(header+12);
    if(mode>1||length!=RING_FILTERED||!same_feature(header+16))return fail();
    if(fread(filtered,1,RING_FILTERED,stdin)!=RING_FILTERED)return fail();
    if(fread(&extra,1,1,stdin)!=0||ferror(stdin))return fail();
    if(ring_unfilter(filtered,rgba)||ring_observe(rgba,&observation))return fail();
    char input_sha[65];
    for(int i=0;i<32;i++)snprintf(input_sha+i*2,3,"%02x",(unsigned)header[48+i]);
    if(append("{\"protocol\":\"ngg2-ring-raw-v1\",\"features_sha256\":\"%s\",\"input_sha256\":\"%s\",\"rows\":[",FIXED_FEATURE_SHA256,input_sha))return fail();
    for(int r=0;r<observation.count;r++){
        int left=observation.rows[r].left,sy=observation.rows[r].sy;
        if(append("%s{\"row\":[%d,%d],\"slots\":[",r?",":"",left,sy))return fail();
        for(int s=0;s<3;s++){
            double score;int box[4];RingWord word;
            if(ring_icon(rgba,RING_RGBA,left+36*s,sy,(int)mode,NULL,&score,box))return fail();
            int word_status=ring_word(&observation,left+36*s,sy,s,&word);
            if(word_status<0)return fail();
            if(append("%s{\"score\":%.17g,\"box\":[%d,%d,%d,%d],\"word\":",s?",":"",score,box[0],box[1],box[2],box[3]))return fail();
            if(word_status==1){
                if(append("null}"))return fail();
            }else if(append("{\"iou\":%.17g,\"coverage\":%.17g,\"box\":[%d,%d,%d,%d]}}",word.iou,word.coverage,word.box[0],word.box[1],word.box[2],word.box[3]))return fail();
        }
        if(append("]}"))return fail();
    }
    if(append("]}\n"))return fail();
    if(fwrite(reply,1,used,stdout)!=used||fflush(stdout)||ferror(stdout))return fail();
    return 0;
}
