"""Discrete min-cost-flow scheduler for preemptible compute and recovered heat."""
import math
from collections import deque

def finite(x,label,low,high):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not low<=x<=high:
        raise ValueError(f"{label} must be finite and in [{low}, {high}]")
    return x

def solve(s):
    carbon=s.get("carbon_g_per_kwh");heat=s.get("heat_demand_kwh")
    if not isinstance(carbon,list) or not 2<=len(carbon)<=48: raise ValueError("Provide 2 to 48 hourly carbon values")
    n=len(carbon)
    if not isinstance(heat,list) or len(heat)!=n: raise ValueError("Heat demand must match the carbon horizon")
    for c in carbon: finite(c,"carbon",0,2000)
    for d in heat: finite(d,"heat demand",0,1000)
    capacity=s.get("capacity_kwh_per_hour",3)
    if type(capacity) is not int or not 1<=capacity<=16: raise ValueError("Capacity must be an integer from 1 to 16 kWh/hour")
    recovery=finite(s.get("heat_recovery",0.8),"heat recovery",0,1)
    displaced=finite(s.get("displaced_heat_g_per_kwh",220),"displaced heat intensity",0,1000)
    jobs=s.get("jobs")
    if not isinstance(jobs,list) or not 1<=len(jobs)<=16: raise ValueError("Provide 1 to 16 jobs")
    for j in jobs:
        if not isinstance(j,dict) or not isinstance(j.get("name"),str) or not j["name"].strip() or len(j["name"])>80: raise ValueError("Each job needs a name up to 80 characters")
        for field in ("release","deadline","energy_kwh"):
            if type(j.get(field)) is not int: raise ValueError("Job windows and energy must be integers")
        if not 0<=j["release"]<j["deadline"]<=n or not 1<=j["energy_kwh"]<=100:
            raise ValueError("Invalid job window or energy (1 to 100 kWh)")
    if len({j['name'] for j in jobs})!=len(jobs): raise ValueError("Job names must be unique")
    def schedule(earliest=False):
        count=2+len(jobs)+n;source=count-2;sink=count-1;g=[[] for _ in range(count)]
        def edge(a,b,cap,cost):
            f=[b,len(g[b]),cap,cost];r=[a,len(g[a]),0,-cost];g[a].append(f);g[b].append(r);return f
        handles=[]
        for i,j in enumerate(jobs):
            edge(source,i,j['energy_kwh'],0)
            for h in range(j['release'],j['deadline']):
                e=edge(i,len(jobs)+h,j['energy_kwh'],0);handles.append((i,h,e,j['energy_kwh']))
        for h in range(n):
            for k in range(capacity):
                recovered=min(recovery,max(0,heat[h]-k*recovery))
                cost=h*100000 if earliest else round(1000*(carbon[h]-displaced*recovered))
                edge(len(jobs)+h,sink,1,cost)
        remaining=sum(j['energy_kwh'] for j in jobs)
        while remaining:
            distance=[math.inf]*count;distance[source]=0;parent=[None]*count;queue=deque([source]);inside={source}
            while queue:
                a=queue.popleft();inside.remove(a)
                for ix,e in enumerate(g[a]):
                    b,rev,cap,cost=e
                    if cap and distance[a]+cost<distance[b]:
                        distance[b]=distance[a]+cost;parent[b]=(a,ix)
                        if b not in inside: queue.append(b);inside.add(b)
            if parent[sink] is None: raise ValueError("No feasible schedule: reduce job energy, widen deadlines, or increase capacity")
            flow=remaining;v=sink
            while v!=source:
                a,ix=parent[v];flow=min(flow,g[a][ix][2]);v=a
            v=sink
            while v!=source:
                a,ix=parent[v];e=g[a][ix];e[2]-=flow;g[v][e[1]][2]+=flow;v=a
            remaining-=flow
        rows=[[0]*n for _ in jobs]
        for i,h,e,cap in handles: rows[i][h]=cap-e[2]
        total=[sum(row[h] for row in rows) for h in range(n)]
        recovered=[min(heat[h],total[h]*recovery) for h in range(n)]
        gross=sum(total[h]*carbon[h] for h in range(n));credit=sum(recovered)*displaced
        return {"allocations":[{"name":j['name'],"slots":rows[i]} for i,j in enumerate(jobs)],"hourly_compute_kwh":total,"hourly_recovered_heat_kwh":recovered,"compute_kwh":sum(total),"recovered_heat_kwh":round(sum(recovered),3),"gross_carbon_g":round(gross,3),"avoided_heat_carbon_g":round(credit,3),"net_carbon_g":round(gross-credit,3)}
    baseline=schedule(True);optimized=schedule()
    return {"baseline":baseline,"optimized":optimized,"net_carbon_reduction_g":round(baseline['net_carbon_g']-optimized['net_carbon_g'],3),"model":"Optimal for preemptible 1 kWh units under this linear forecast model; heat credits are counterfactual, not measured carbon removal"}
