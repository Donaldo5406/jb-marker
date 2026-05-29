import os
from huggingface_hub import HfApi

RID = "Doss-8b-instruct/jb-marker"
api = HfApi(token=os.environ["HF_TOKEN"])
key, val, target = os.environ["KEY"], os.environ["VALUE"], os.environ["TARGET"]
if target == "hf-secret":
    raise SystemExit("hf-secret not allowed via set-env — use gh secret set / HF dashboard")
api.add_space_variable(RID, key, val)
api.restart_space(RID)
print(f"set {target} {key} + restarted {RID}")
