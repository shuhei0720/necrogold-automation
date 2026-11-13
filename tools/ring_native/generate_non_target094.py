"""Generate bounded C numeric constants; no original image is an input."""
import argparse
import hashlib
import json
from pathlib import Path

BANK_SHA='243a57fa6e5cb7255d7b8f9d1deea2d4e9c4502dd0b591be1185c066fa566cd7'
COVERAGE_SHA='061a3989de2729ea4f327976b8d265f14f6918aaccb42a9cd932356623a3abb4'


def load(path,digest):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('fixed_feature_identity')
    return json.loads(raw)


def icon_arrays(lines,key,icon):
    w,h=icon['width'],icon['height'];bright,dark=icon['bright'],icon['dark']
    if not (1<=w<=36 and 1<=h<=36 and 1<=len(bright)<=1296 and 1<=len(dark)<=1296):raise ValueError('icon_bounds')
    for row in bright:
        if len(row)!=5 or not (0<=row[0]<w and 0<=row[1]<h and all(type(v) is int and 0<=v<=255 for v in row[2:])):raise ValueError('bright_bounds')
    for row in dark:
        if len(row)!=2 or not (0<=row[0]<w and 0<=row[1]<h):raise ValueError('dark_bounds')
    intensities=[sum(p[2:]) for p in bright];total=sum(intensities)
    energy=sum(sum(c*c for c in p[2:]) for p in bright)
    variance=sum(v*v for v in intensities)-total*total/len(bright)
    if (icon['energy'],icon['target_sum'],icon['target_var'])!=(energy,total,variance):raise ValueError('icon_moments')
    if not (0<energy<2**31 and 0<total<2**31 and variance>0):raise ValueError('moment_bounds')
    lines.append('static const R94BankBright '+key+'_bright[] = {'+','.join('{'+','.join(map(str,p))+'}' for p in bright)+'};')
    lines.append('static const R94BankDark '+key+'_dark[] = {'+','.join('{'+','.join(map(str,p))+'}' for p in dark)+'};')
    return '{%d,%d,%d,%d,%s_bright,%s_dark,INT32_C(%d),INT32_C(%d),%s}'%(w,h,len(bright),len(dark),key,key,energy,total,variance.hex())


def word_array(lines,key,word,max_height=12,max_width=96):
    w,h,ink=word['width'],word['height'],word['ink'];rows=[int(row,16) for row in word['rows_hex']]
    if not (1<=w<=max_width and 1<=h<=max_height and len(rows)==h and ink==sum(v.bit_count() for v in rows) and ink>0 and all(0<=v<1<<w for v in rows)):raise ValueError('word_bounds')
    lines.append('static const uint64_t '+key+'[][2] = {'+','.join('{UINT64_C(0x%016x),UINT64_C(0x%016x)}'%(v&((1<<64)-1),v>>64) for v in rows)+'};')
    return w,h,ink


def outputs(bank_path,coverage_path):
    bank=load(bank_path,BANK_SHA);auth=load(coverage_path,COVERAGE_SHA)
    if bank['schema']!='ngg2-exposed-goods-bank-v2' or not 1<=len(bank['entries'])<=16:raise ValueError('bank_schema')
    if auth['schema']!='ngg2-goldshop-auth-features-v1' or not 1<=len(auth['shop_glyphs'])<=4 or not 1<=len(auth['merchant_icons'])<=2:raise ValueError('auth_schema')
    base=['/* Generated numeric features only. Provenance/ROIs are in the fixed JSON. */','#ifndef NG2_RING_BANK_H','#define NG2_RING_BANK_H','#include <stdint.h>',
      'typedef struct { uint8_t dx,dy,r,g,b; } R94BankBright;',
      'typedef struct { uint8_t dx,dy; } R94BankDark;',
      'typedef struct { uint16_t width,height,count,dark_count; const R94BankBright *bright; const R94BankDark *dark; int32_t energy,target_sum; double target_var; } R94BankIcon;',
      'typedef struct { uint16_t width,height,gold_ink,dark_ink; const uint64_t (*gold_rows)[2]; const uint64_t (*dark_rows)[2]; } R94ContainerShape;',
      'typedef struct { uint32_t id; const char *label; const R94BankIcon *icons; uint16_t icon_count,word_width,word_height,word_ink; const uint64_t (*word_rows)[2]; uint16_t kind; const R94ContainerShape *container_shape; } R94BankEntry;',
      '#define R94_BANK_NONTARGET 1',
      '#define R94_BANK_IGNORED_CONTAINER 2',
      '#define R94_SCOPE_POLICY_VERSION "exposed-cursed-ring-only-user-2026-11-13"',
      '#define R94_BANK_SHA256 "'+BANK_SHA+'"',
      '#define R94_BANK_COUNT '+str(len(bank['entries'])),
      '_Static_assert(INT64_C(1296)*765*765<INT32_MAX,"bank moment bound");']
    entries=[];seen=set()
    for e in bank['entries']:
        if type(e['id']) is not int or not 1<=e['id']<=16 or e['id'] in seen:raise ValueError('bank_id')
        seen.add(e['id']);name='r94_bank_'+str(e['id']);sprites=[]
        if not 1<=len(e['icons'])<=3:raise ValueError('bank_icon_count')
        for i,sp in enumerate(e['icons']):sprites.append(icon_arrays(base,name+'_'+str(i),sp))
        base.append('static const R94BankIcon '+name+'_icons[] = {'+','.join(sprites)+'};')
        if e['kind']=='non_target':
            if e['container_shape'] is not None:raise ValueError('named_item_shape')
            w,h,ink=word_array(base,name+'_word',e['word'])
            entries.append('{%d,%s,%s_icons,%d,%d,%d,%d,%s_word,R94_BANK_NONTARGET,0}'%(e['id'],json.dumps(e['label'],ensure_ascii=False),name,len(sprites),w,h,ink,name))
        elif e['kind']=='ignored_container':
            if e['word'] is not None:raise ValueError('container_word')
            shape=e['container_shape'];w,h=shape['width'],shape['height']
            for component in ('gold','dark'):
                word_array(base,name+'_'+component,dict(width=w,height=h,ink=shape[component+'_ink'],rows_hex=shape[component+'_rows_hex']),36,36)
            base.append('static const R94ContainerShape '+name+'_shape = {%d,%d,%d,%d,%s_gold,%s_dark};'%(w,h,shape['gold_ink'],shape['dark_ink'],name,name))
            entries.append('{%d,%s,%s_icons,%d,0,0,0,0,R94_BANK_IGNORED_CONTAINER,&%s_shape}'%(e['id'],json.dumps(e['label'],ensure_ascii=False),name,len(sprites),name))
        else:raise ValueError('bank_kind')
    base.append('static const R94BankEntry r94_bank_entries[] = {'+','.join(entries)+'};');base+=['#endif','']
    cover=['/* Generated limited gold-shop authentication features; no original raster. */','#ifndef NG2_RING_COVERAGE_H','#define NG2_RING_COVERAGE_H','#include "NG2RingBank.h"',
      'typedef struct { uint16_t width,height,ink; const uint64_t (*rows)[2]; } R94CoverageGlyph;',
      '#define R94_COVERAGE_SHA256 "'+COVERAGE_SHA+'"',
      '#define R94_COVERAGE_AUTHORITY_VERSION "'+auth['coverage_authority_version']+'"',
      '#define R94_SHOP_GLYPH_COUNT '+str(len(auth['shop_glyphs'])),
      '#define R94_MERCHANT_COUNT '+str(len(auth['merchant_icons']))]
    glyphs=[]
    for i,g in enumerate(auth['shop_glyphs']):
        name='r94_shop_glyph_'+str(i);w,h,ink=word_array(cover,name,g)
        glyphs.append('{%d,%d,%d,%s}'%(w,h,ink,name))
    cover.append('static const R94CoverageGlyph r94_shop_glyphs[] = {'+','.join(glyphs)+'};')
    merchants=[]
    for i,sp in enumerate(auth['merchant_icons']):merchants.append(icon_arrays(cover,'r94_merchant_'+str(i),sp))
    cover.append('static const R94BankIcon r94_merchants[] = {'+','.join(merchants)+'};');cover+=['#endif','']
    return {'NG2RingBank.h':'\n'.join(base),'NG2RingCoverage.h':'\n'.join(cover)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--bank',type=Path,required=True);p.add_argument('--coverage',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--check',action='store_true');args=p.parse_args()
    for name,body in outputs(args.bank,args.coverage).items():
        path=args.output/name
        if args.check:
            if path.read_bytes()!=body.encode():raise ValueError('generated_features_changed')
        else:path.write_text(body)
if __name__=='__main__':main()
