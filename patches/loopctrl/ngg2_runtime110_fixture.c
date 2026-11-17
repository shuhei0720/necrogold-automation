/* Procedural incomplete classifier result only. The actual production Runtime
 * worker still hashes and calls the actual kernel on its retained RGBA. */
#include "ngg2_cycle_runtime_fixture.h"
void ng2_fixture_partial_unknown110(const NG2Scene *scene,uint64_t start,uint64_t end,NG2RingResult *out){
    int i;ng2_fixture_cycle_result(scene,start,end,NG2_RING_UNKNOWN,out);
    out->coverage=NG2_RING_COVERAGE_INCOMPLETE;out->partial_safe_no_positive=1;
    out->row_count=1;out->selected_row=0;
    out->rows[0].left=300;out->rows[0].sy=90;out->rows[0].word_slot=-1;
    for(i=0;i<3;++i){NG2RingSlot *s=&out->rows[0].slots[i];
        s->cx=300+36*i;s->sy=90;s->slot=i;s->icon_score=s->icon_upper_bound=.1;
    }
}
