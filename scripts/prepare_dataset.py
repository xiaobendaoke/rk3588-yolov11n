#!/usr/bin/env python3
import json, os, shutil
from pathlib import Path
from collections import defaultdict

COCO_DIR = Path("/mnt/hgfs/coco")
CUSTOM_DIR = Path("/mnt/hgfs/Detecting working desk.v1i.yolov11")

COCO_NAMES = [
    'person','bicycle','car','motorcycle','airplane','bus','train',
    'truck','boat','traffic light','fire hydrant','stop sign',
    'parking meter','bench','bird','cat','dog','horse','sheep','cow',
    'elephant','bear','zebra','giraffe','backpack','umbrella','handbag',
    'tie','suitcase','frisbee','skis','snowboard','sports ball','kite',
    'baseball bat','baseball glove','skateboard','surfboard',
    'tennis racket','bottle','wine glass','cup','fork','knife','spoon',
    'bowl','banana','apple','sandwich','orange','broccoli','carrot',
    'hot dog','pizza','donut','cake','chair','couch','potted plant',
    'bed','dining table','toilet','tv','laptop','mouse','remote',
    'keyboard','cell phone','microwave','oven','toaster','sink',
    'refrigerator','book','clock','vase','scissors','teddy bear',
    'hair drier','toothbrush'
]

C2M = {
    'bottle':39,'cell phone':67,'cup':41,'cutter':80,
    'fork':42,'keyboard':66,'knife':43,'mouse':64,
    'remote':65,'scissors':76,'spoon':44
}

ALL_NAMES = COCO_NAMES + ['cutter']

def convert_coco(json_path, img_dir, out_lbl_dir, tag):
    print(f"[{tag}] Converting COCO...")
    with open(json_path) as f:
        d = json.load(f)
    cats = sorted(d['categories'], key=lambda x: x['id'])
    cid2idx = {c['id']: i for i, c in enumerate(cats)}
    i2a = defaultdict(list)
    for a in d['annotations']:
        i2a[a['image_id']].append(a)
    i2i = {i['id']: i for i in d['images']}
    ok = skip_img = no_lbl = 0
    for img_id, anns in i2a.items():
        info = i2i[img_id]
        src = img_dir / info['file_name']
        if not src.exists():
            skip_img += 1
            continue
        lines = []
        for a in anns:
            if a['category_id'] not in cid2idx:
                continue
            ci = cid2idx[a['category_id']]
            x,y,bw,bh = a['bbox']
            w,h = info['width'], info['height']
            if w==0 or h==0:
                continue
            xc = max(0, min(1, (x+bw/2)/w))
            yc = max(0, min(1, (y+bh/2)/h))
            bn = max(0, min(1, bw/w))
            hn = max(0, min(1, bh/h))
            lines.append(f"{ci} {xc:.6f} {yc:.6f} {bn:.6f} {hn:.6f}")
        if lines:
            lbl = out_lbl_dir / (Path(info['file_name']).stem + '.txt')
            lbl.parent.mkdir(parents=True, exist_ok=True)
            lbl.write_text('\n'.join(lines))
            ok += 1
        else:
            no_lbl += 1
    print(f"[{tag}] COCO done: {ok} labels, {skip_img} missing, {no_lbl} no-labels")

def remap_custom(split, out_lbl_dir, out_img_dir):
    src_lbl = CUSTOM_DIR / split / 'labels'
    src_img = CUSTOM_DIR / split / 'images'
    if not src_lbl.exists():
        return 0
    import yaml
    with open(CUSTOM_DIR / 'data.yaml') as f:
        cnames = yaml.safe_load(f)['names']
    ok = 0
    for lf in src_lbl.iterdir():
        if lf.suffix != '.txt':
            continue
        stem = lf.stem
        img = src_img / f"{stem}.jpg"
        if not img.exists():
            img = src_img / f"{stem}.png"
        if not img.exists():
            continue
        shutil.copy2(img, out_img_dir / img.name)
        lines = []
        for line in lf.read_text().strip().split('\n'):
            if not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            ni = C2M.get(cnames[int(parts[0])])
            if ni is None:
                print(f"  WARN: unknown class id {parts[0]}")
                continue
            lines.append(f"{ni} " + ' '.join(parts[1:]))
        if lines:
            p = out_lbl_dir / lf.name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('\n'.join(lines))
            ok += 1
    return ok

def main():
    print("=" * 60)
    COCO_DIR.mkdir(parents=True, exist_ok=True)

    coco_lbl_train = COCO_DIR / 'labels' / 'train2017'
    coco_lbl_val = COCO_DIR / 'labels' / 'val2017'
    coco_lbl_test = COCO_DIR / 'labels' / 'test2017'
    coco_img_test = COCO_DIR / 'test2017'

    tj = COCO_DIR / 'annotations' / 'instances_train2017.json'
    vj = COCO_DIR / 'annotations' / 'instances_val2017.json'

    if tj.exists():
        convert_coco(tj, COCO_DIR/'train2017', coco_lbl_train, 'train')
    if vj.exists():
        convert_coco(vj, COCO_DIR/'val2017', coco_lbl_val, 'val')

    n_train = remap_custom('train', coco_lbl_train, COCO_DIR/'train2017')
    n_val = remap_custom('valid', coco_lbl_val, COCO_DIR/'val2017')
    n_test = remap_custom('test', coco_lbl_test, coco_img_test)
    print(f"Custom: train={n_train} val={n_val} test={n_test}")

    yaml_txt = f"""train: {COCO_DIR}/train2017
val: {COCO_DIR}/val2017
test: {COCO_DIR}/test2017
nc: {len(ALL_NAMES)}
names: {ALL_NAMES}
"""
    (COCO_DIR / 'data.yaml').write_text(yaml_txt)
    print(f"data.yaml -> {len(ALL_NAMES)} classes")

    for d, tag in [(COCO_DIR/'train2017','train'),(COCO_DIR/'val2017','val'),(COCO_DIR/'test2017','test')]:
        if d.exists():
            lbl = COCO_DIR / 'labels' / d.name
            imgs = len(list(d.iterdir()))
            lbls = len(list(lbl.iterdir())) if lbl.exists() else 0
            print(f"  {tag}: {imgs} imgs, {lbls} labels")
    print("=" * 60)

if __name__ == '__main__':
    main()