"""Compare each completed Engine run with a separately replayed trade ledger."""
from verify import *
def compare(files):
 verified={}
 with tempfile.TemporaryDirectory() as tmp:
  m=Market('eth',tmp);rv=Review(m)
  for label,file in files.items():
   result=json.loads(Path(file).read_bytes())
   if result.get('status')!='completed':
    verified[label]={'status':'unverified','reason':result.get('message')};continue
   args=CASES[label];a,meta,_=audit(m,rv,7,170,*args)
   root=Path.home()/'BBB_data/research/runs'/result['run_id']
   fills=sorted(json.loads((root/'trades.json').read_bytes()),key=lambda v:v['entry_bar_index'])
   assert len(fills)==len(a)
   for i,(exp,fill) in enumerate(zip(a,fills)):
    assert (exp[0],exp[1],exp[2])==(fill['entry_bar_index'],fill['exit_bar_index'],1 if fill['side']=='long' else -1),(label,i)
    np.testing.assert_allclose(exp[3:5],[float(fill['entry_price']),float(fill['exit_price'])],atol=1e-7,rtol=0)
   native_be=sum(f['exit_rule_id']=='adx-be' for f in fills)
   assert native_be==sum(r[-1]=='BE' for r in meta)
   verified[label]=dict(status='matched',run_id=result['run_id'],trades=len(a),be=native_be,solo_net=result['net_pnl'],market_data_hash=result['market_data_hash'])
 return verified
if __name__=='__main__':
 files=dict(frequent='/tmp/prot_native_result.json',**{'15m':'/tmp/prot_result_15m.json','1h':'/tmp/prot_result_1h.json'})
 (OUT/'engine_checks.json').write_text(json.dumps(compare(files),indent=2)+'\n')
