from tqdm import tqdm
import time


for i in tqdm(range(1000)):
    print(i)
    time.sleep(0.1)
