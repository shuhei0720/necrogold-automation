#include "ring.h"
#include <stdlib.h>
#include <string.h>

int ring_unfilter(const unsigned char *filtered,unsigned char *rgba){
    const int stride=RING_W*4;
    if(!filtered||!rgba)return -1;
    for(int y=0;y<RING_HH;y++){
        int method=filtered[(size_t)y*(stride+1)];
        if(method>4)return -1;
        unsigned char *row=rgba+(size_t)y*stride;
        const unsigned char *prior=y?row-stride:NULL;
        memcpy(row,filtered+(size_t)y*(stride+1)+1,(size_t)stride);
        if(method==1){
            for(int i=4;i<stride;i++)row[i]=(unsigned char)(row[i]+row[i-4]);
        }else if(method==2){
            if(prior)for(int i=0;i<stride;i++)row[i]=(unsigned char)(row[i]+prior[i]);
        }else if(method==3||method==4){
            for(int i=0;i<stride;i++){
                int a=i>=4?row[i-4]:0,b=prior?prior[i]:0,estimate;
                if(method==3)estimate=(a+b)/2;
                else{
                    int c=prior&&i>=4?prior[i-4]:0,p=a+b-c;
                    int da=abs(p-a),db=abs(p-b),dc=abs(p-c);
                    estimate=da<=db&&da<=dc?a:db<=dc?b:c;
                }
                row[i]=(unsigned char)(row[i]+estimate);
            }
        }
        for(int i=3;i<stride;i+=4)if(row[i]!=255)return -1;
    }
    return 0;
}
