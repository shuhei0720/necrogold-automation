#include "ngg2_cycle_runtime_fixture.h"
#include <string.h>
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
