import os
from huggingface_hub import HfApi

RID = "Doss-8b-instruct/jb-marker"
api = HfApi(token=os.environ["HF_TOKEN"])
key, val, target = os.environ["KEY"], os.environ["VALUE"], os.environ["TARGET"]
if target == "hf-secret":
    api.add_space_secret(RID, key, val)
else:
    api.add_space_variable(RID, key, val)
api.restart_space(RID)
print(f"set {target} {key} + restarted {RID}")
