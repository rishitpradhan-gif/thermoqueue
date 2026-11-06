import copy,itertools,json,unittest
from pathlib import Path
from engine import solve
SAMPLE=json.loads((Path(__file__).parents[1]/"examples/scenario.json").read_text())
class SchedulingTests(unittest.TestCase):
    def test_energy_capacity_and_deadlines(self):
        r=solve(SAMPLE)
        for plan in (r['baseline'],r['optimized']):
            for j,row in zip(SAMPLE['jobs'],plan['allocations']):
                self.assertEqual(sum(row['slots']),j['energy_kwh'])
                self.assertTrue(all(v==0 for h,v in enumerate(row['slots']) if not j['release']<=h<j['deadline']))
            self.assertTrue(all(v<=SAMPLE['capacity_kwh_per_hour'] for v in plan['hourly_compute_kwh']))
    def test_heat_credit_never_exceeds_demand_or_recovery(self):
        r=solve(SAMPLE)['optimized']
        for h,heat in enumerate(r['hourly_recovered_heat_kwh']):
            self.assertLessEqual(heat,SAMPLE['heat_demand_kwh'][h]+1e-9);self.assertLessEqual(heat,r['hourly_compute_kwh'][h]*SAMPLE['heat_recovery']+1e-9)
    def test_optimizer_is_not_worse_than_earliest(self):
        r=solve(SAMPLE);self.assertLessEqual(r['optimized']['net_carbon_g'],r['baseline']['net_carbon_g'])
    def test_exact_against_bruteforce(self):
        s={'carbon_g_per_kwh':[260,100,180],'heat_demand_kwh':[.6,0,1.3],'capacity_kwh_per_hour':2,'heat_recovery':.7,'displaced_heat_g_per_kwh':220,'jobs':[{'name':'A','release':0,'deadline':2,'energy_kwh':2},{'name':'B','release':1,'deadline':3,'energy_kwh':1}]}
        candidates=[]
        for a in itertools.product(range(2),repeat=2):
            for b in (1,2):
                load=[a.count(h)+int(b==h) for h in range(3)]
                if max(load)>2:continue
                candidates.append(sum(load[h]*s['carbon_g_per_kwh'][h]-min(s['heat_demand_kwh'][h],load[h]*.7)*220 for h in range(3)))
        self.assertAlmostEqual(solve(s)['optimized']['net_carbon_g'],min(candidates),places=3)
    def test_no_heat_chooses_cleanest_hours(self):
        s={'carbon_g_per_kwh':[400,100,200],'heat_demand_kwh':[0,0,0],'capacity_kwh_per_hour':1,'jobs':[{'name':'A','release':0,'deadline':3,'energy_kwh':2}]}
        self.assertEqual(solve(s)['optimized']['hourly_compute_kwh'],[0,1,1])
    def test_recovered_heat_can_change_the_preferred_hour(self):
        s={'carbon_g_per_kwh':[200,100],'heat_demand_kwh':[1,0],'capacity_kwh_per_hour':1,'heat_recovery':1,'displaced_heat_g_per_kwh':180,'jobs':[{'name':'A','release':0,'deadline':2,'energy_kwh':1}]}
        self.assertEqual(solve(s)['optimized']['hourly_compute_kwh'],[1,0]);s['displaced_heat_g_per_kwh']=0;self.assertEqual(solve(s)['optimized']['hourly_compute_kwh'],[0,1])
    def test_infeasible_demand(self):
        s=copy.deepcopy(SAMPLE);s['jobs'][0]['energy_kwh']=100
        with self.assertRaisesRegex(ValueError,'No feasible'):solve(s)
    def test_invalid_inputs(self):
        for patch in [{'capacity_kwh_per_hour':0},{'heat_recovery':1.5},{'heat_demand_kwh':[]},{'carbon_g_per_kwh':[float('nan'),1]},{'jobs':[{'name':'A','release':0,'deadline':0,'energy_kwh':1}]}]:
            with self.subTest(patch=patch),self.assertRaises(ValueError):solve({**SAMPLE,**patch})
