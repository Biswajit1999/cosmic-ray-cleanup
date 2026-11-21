"""Generate a labelled synthetic threshold sensitivity figure; not HST data."""
from pathlib import Path
import importlib.util
import numpy as np
import matplotlib.pyplot as plt
spec = importlib.util.spec_from_file_location("audit", Path(__file__).with_name("conditional_audit.py"))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
scores = np.array([.05,.1,.2,.35,.6,.7,.8,.95])
truth = np.array([0,0,0,1,0,1,1,1], dtype=bool)
core = np.array([0,0,0,0,1,0,0,0], dtype=bool)
cuts = np.linspace(.05,.95,40)
curve = audit.threshold_curve(scores,truth,cuts,core)
for i,label in enumerate(["Precision","Recall","Source-core false masking"]):
    plt.plot(cuts,curve[:,i],label=label)
plt.xlabel("Synthetic score threshold")
plt.ylabel("Fraction")
plt.title("Synthetic conditional cosmic-ray audit — not HST data")
plt.legend()
plt.tight_layout()
plt.savefig("synthetic_cosmic_threshold_audit.png",dpi=160)
