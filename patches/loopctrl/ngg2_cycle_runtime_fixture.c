#include "ngg2_cycle_runtime_fixture.h"
#include "ngg2_runtime_scene_fixtures.h"
#include <string.h>
int ng2_fixture_cycle_search_rgba(uint8_t *out,size_t length,int32_t world_x,int32_t variant,int32_t goods){
    size_t at;int x,y,col,row;
    if(!out||length!=896u*414u*4u||variant<0||variant>1||goods<0||goods>2)return 0;
    if(!ng2_fixture_floor_pixels_rgba(out,length,world_x,0,.5,goods?1:0))return 0;
    if(!goods)for(at=0;at<length;at+=4)
        if(out[at]>=180&&out[at+1]>=140&&out[at+2]<=90){out[at]=26;out[at+1]=16;out[at+2]=16;}
    if(variant)for(row=2;row<=3;++row)for(col=0;col<8;++col){
        if(col!=0&&col!=6&&col!=7)continue;
        for(y=70+row*48;y<118+row*48;++y)for(x=224+col*56;x<280+col*56;++x){
            int shade;at=((size_t)y*896+(size_t)x)*4;
            if(out[at]<22||out[at]>30||out[at+1]<12||out[at+1]>20||out[at+2]<12||out[at+2]>20)continue;
            shade=80+(int)out[at]-26;out[at]=out[at+1]=out[at+2]=(uint8_t)shade;
        }
    }
    if(goods==2)for(y=132;y<170;++y)for(x=250;x<286;++x){
        at=((size_t)y*896+(size_t)x)*4;out[at]=26;out[at+1]=16;out[at+2]=16;
    }
    return 1;
}
static void box(int32_t out[4],int x,int y,int w,int h){out[0]=x;out[1]=y;out[2]=w;out[3]=h;}
void ng2_fixture_cycle_result(const NG2Scene *scene,uint64_t started,uint64_t finished,
    int outcome,NG2RingResult *out){
    int side,index;NG2RingRow *row;NG2RingCoverage *w;
    memset(out,0,sizeof(*out));out->abi=NG2_RING_ABI;out->size=sizeof(*out);
    out->started_ns=started;out->finished_ns=finished;out->outcome=(uint32_t)outcome;
    out->selected_row=out->selected_partial=-1;
    if(outcome!=NG2_RING_NEGATIVE)return;
    out->coverage=NG2_RING_COVERAGE_COMPLETE;out->row_count=1;out->selected_row=0;
    row=&out->rows[0];row->left=300;row->sy=90;row->word_slot=-1;row->outcome=NG2_RING_NEGATIVE;
    w=&out->certificate;w->layout_version=w->policy_version=w->accepted_rows=1;
    w->board_mode=1;
    w->scene_state=NG2_FLOOR;w->scene_goods=NG2_GOODS_VISIBLE;
    if(scene)for(index=0;index<NG2_TILE_COUNT;++index)w->actual_gold_cells+=scene->tiles[index]==NG2_TILE_GOLD;
    w->observed_items=w->observed_prices=w->non_target_items=3;w->row[0]=300;w->row[1]=90;
    box(w->strip_box,246,114,180,65);box(w->merchant_box,326,80,20,20);
    w->merchant_score=w->merchant_coverage=1.0;
    for(side=0;side<2;++side){
        NG2RingEndcap *end=&w->endcaps[side];
        box(w->sign_boxes[side],289+72*side,84,22,7);box(w->board_boxes[side],288+72*side,80,24,20);
        w->board_counts[side]=200;w->sign_iou[side]=w->sign_coverage[side]=1.0;
        box(end->box,252+144*side,126,25,25);end->r=25;end->g=15;end->b=14;end->spread=1;end->count=625;
        end->floor_full=end->floor_upper=end->floor_lower=1;
    }
    for(index=0;index<3;++index){
        NG2RingSlot *slot=&row->slots[index];slot->cx=300+36*index;slot->sy=90;slot->slot=index;
        slot->icon_score=slot->icon_upper_bound=.1;slot->icon_score_exact=1;
        slot->outcome=NG2_RING_NON_TARGET;slot->kind=1;slot->non_target_id=(uint32_t)index+1;
        slot->non_target_icon_score=slot->non_target_name_iou=slot->non_target_name_coverage=1.0;
        box(slot->non_target_icon_box,slot->cx-6,124,13,13);box(slot->non_target_name_box,slot->cx-6,145,13,7);
        memcpy(w->item_boxes[index],slot->non_target_icon_box,sizeof(w->item_boxes[index]));
        memcpy(w->name_boxes[index],slot->non_target_name_box,sizeof(w->name_boxes[index]));
        box(w->price_boxes[index],slot->cx-4,159,9,7);
    }
}
