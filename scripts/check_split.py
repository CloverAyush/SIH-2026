import pandas as pd, os
from sklearn.model_selection import train_test_split
TAB=r'c:\Users\OM CHICKS\Desktop\SIH Final\data\DARTIS_2019.tab'
df=pd.read_csv(TAB, sep='\t', skiprows=49, header=0)
all_paths=[]
all_labels=[]
DATA_DIR=r'c:\Users\OM CHICKS\Desktop\SIH Final\data\DARTIS'
for idx,row in df.iterrows():
    image_class=str(row.iloc[0]).lower()
    image_name=str(row.iloc[1])
    full_path=os.path.join(DATA_DIR,image_name)
    if os.path.exists(full_path):
        all_paths.append(image_name)
        label=1 if ('oc' in image_class or 'ow' in image_class) else 0
        all_labels.append(label)
train_paths,val_paths,train_labels,val_labels=train_test_split(all_paths,all_labels,test_size=0.20, random_state=42)
print('total',len(all_paths),'train',len(train_paths),'val',len(val_paths))
print('ow-0450 in train?', 'ow-0450.jpg' in train_paths)
print('ow-0450 in val?', 'ow-0450.jpg' in val_paths)
for idx,row in df.iterrows():
    if str(row.iloc[1])=='ow-0450.jpg':
        print('tab_class:',row.iloc[0])
        break
