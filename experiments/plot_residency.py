"""Plot measured Experiment 005 seed-level results; no smoothing or interpolation."""
from pathlib import Path
import csv
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'results' / 'experiment_005'
rows = list(csv.DictReader((path / 'trials.csv').open(encoding='utf-8')))
groups = ('founder','dense','islands','islands_costly')
titles = ('Founders','Dense-trained','Island-trained','Costly-island-trained')
for scenario, metric, title, ylabel, fname in (
    ('search','hit_fraction','Searching for a food core','Fraction entering any core','search_arrival.png'),
    ('residence','occupancy_fraction','Remaining in a food core','Fraction of time in a core','core_residency.png'),
    ('residence','harvest_per_agent_tick','Resource intake after starting in a core','Food units / agent / tick','resident_harvest.png'),
):
    fig,ax=plt.subplots(figsize=(10.2,5.4))
    x=np.arange(len(groups),dtype=float)
    width=.36
    for offset,mode,label in ((-width/2,'speed_fixed','Natural controller'),(width/2,'fixed_zero_turn','Turning removed')):
        outcomes=[[float(r[metric]) for r in rows if r['group']==g and r['start']==scenario and r['mode']==mode]
                  for g in groups]
        means=[np.mean(v) for v in outcomes]
        ax.bar(x+offset,means,width,label=label)
        # Replicate-level dots, not 36 independent pseudoreplicates per trial.
        for i,y in enumerate(outcomes):
            ax.scatter(np.repeat(x[i]+offset,len(y)),y,s=12,zorder=3)
    ax.set_xticks(x,titles)
    ax.set_ylabel(ylabel)
    ax.set_title(title+'  •  8 independent seeds / condition')
    ax.legend(loc='upper left' if scenario=='residence' else 'upper right')
    ax.grid(axis='y',alpha=.18)
    fig.text(.01,.01,'Both controllers fixed at speed 0.60 · 75-tick probes · Exploratory analysis',fontsize=9)
    fig.tight_layout(rect=[0,.03,1,1])
    fig.savefig(path/fname,dpi=160)
    plt.close(fig)
# Additional intervention that tests direct resource sensing against generic motor turning.
fig,ax=plt.subplots(figsize=(9,5))
for group in ('founder','islands_costly'):
    selected=[r for r in rows if r['group']==group and r['start']=='residence']
    vals=[np.mean([float(r['occupancy_fraction']) for r in selected if r['mode']==mode])
          for mode in ('speed_fixed','fixed_zero_turn','fixed_food_blind','fixed_mirror_food')]
    ax.plot(('Normal','No steering','Food blind','Food cues mirrored'),vals,marker='o',label=group)
ax.set_title('Food-sensor ablation does not abolish retention')
ax.set_ylabel('Fraction of ticks inside a food core')
ax.grid(alpha=.18)
ax.legend()
fig.tight_layout()
fig.savefig(path/'sensory_ablations.png',dpi=160)
plt.close(fig)
