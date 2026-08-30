import os, sys, torch, cv2, numpy as np
# add src to path
repo = r'C:\Users\OM CHICKS\Desktop\SIH Final'
src = os.path.join(repo, 'src')
sys.path.append(src)
from core.gatekeeper import RobustGatekeeperCNN

# paths
models_dir = os.path.join(repo, 'models')
model_path = os.path.join(models_dir, 'robust_gatekeeper_best.pth')
if not os.path.exists(model_path):
    print('MODEL MISSING', model_path)
    raise SystemExit(1)

# parse tab for positive entries
tab = os.path.join(repo, 'data', 'DARTIS_2019.tab')
positives = []
with open(tab, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip()=='' or line.startswith('/*'):
            continue
        parts = line.strip().split('\t')
        if len(parts) < 2:
            continue
        cls = parts[0].lower()
        fname = parts[1]
        if cls.startswith('ow') or cls.startswith('oc') or cls=='ow' or cls=='oc':
            positives.append((fname, cls))

# unique
seen=set(); positives2=[]
for fn,cls in positives:
    if fn in seen: continue
    seen.add(fn); positives2.append((fn,cls))
positives=positives2

print('Found positive entries in tab:', len(positives))
# filter those whose files exist under data/DARTIS
data_dir = os.path.join(repo, 'data','DARTIS')
existing=[]
for fn,cls in positives:
    path = os.path.join(data_dir, fn)
    if os.path.exists(path):
        existing.append((fn,cls,path))

print('Positive images present on disk:', len(existing))
# limit maybe to first 200
existing = existing[:200]

# load model
device = torch.device('cpu')
model = RobustGatekeeperCNN().to(device)
state = torch.load(model_path, map_location=device)
model.load_state_dict(state)
model.eval()

results=[]
for fn,cls,path in existing:
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        continue
    img_resized = cv2.resize(img, (224,224)).astype(np.float32)/255.0
    img_resized = (img_resized - 0.5)/0.5
    tensor = torch.from_numpy(img_resized).unsqueeze(0).unsqueeze(0).to(device)
    with torch.no_grad():
        out = model(tensor)
        prob = torch.sigmoid(out).item()
    results.append((fn, cls, prob))

# sort top 5 by prob desc
results_sorted = sorted(results, key=lambda x: x[2], reverse=True)
print('\nTop 10 results:')
for r in results_sorted[:10]:
    print(r[0],'|',r[1],'|',r[2])

# print count of positives
print('\nTotal evaluated:', len(results))
