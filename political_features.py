"""Extra political strategy systems for MP Career Mode; all outcomes are fictional."""
import json, random
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from content_store import load_json, load_press_stories

DATA_DIR = Path(__file__).resolve().parent / "data"
ISSUES = {
 "Transport": ["Local rail and bus links", "High-speed rail route", "Congestion and journey times"],
 "Housing": ["Affordable homes", "Planning and green-belt pressure", "Rent and housing quality"],
 "Public services": ["GP and hospital access", "School capacity", "Social care"],
 "Jobs and growth": ["High-street vacancies", "Skills and apprenticeships", "Small-business costs"],
 "Environment": ["Flood protection", "Clean energy infrastructure", "Nature and green space"],
}
LEAKS = [(x['title'], x['detail'], x['boost'], x['risk']) for x in load_press_stories()]
DEPARTMENTS = ["Transport Secretary", "Chancellor", "Health Secretary", "Housing Secretary", "Environment Secretary"]

def clamp(v, lo=0, hi=100): return max(lo, min(hi, int(round(v))))
def record(p, title, text):
 p.setdefault("history", []).append({"title":title,"text":text,"term":p.get("career_term",1),"year":p.get("career_year",1),"session":p.get("career_session",1)})
 p["last_event"] = text

def ensure(p):
 f=p.setdefault("political_features",{})
 defaults={"leaks":[],"polls":[],"national":25.0,"local":int(p.get("stats",{}).get("constituency_support",58)),"inflation":3.2,"tax":50,"reshuffle_count":0}
 for k,v in defaults.items(): f.setdefault(k,v)
 if not f["polls"]: f["polls"].append({"Session":0,"National party support":f["national"],"Constituency approval":f["local"]})
 return f

def seat_data(p):
 seat={}
 try:
  rows=load_json("constituencies_2024.json").get("constituencies",[])
  seat=next((r for r in rows if r.get("name")==p.get("constituency")),{})
 except (OSError,ValueError,TypeError): pass
 geo_code=None
 try:
  with (DATA_DIR/"constituencies_2024.geojson").open(encoding="utf-8") as h: geo=json.load(h)
  feat=next((x for x in geo.get("features",[]) if x.get("properties",{}).get("PCON24NM")==p.get("constituency")),None)
  if feat: geo_code=feat.get("properties",{}).get("PCON24CD")
 except (OSError,json.JSONDecodeError): pass
 return seat,geo_code

def render(p):
 if not isinstance(p,dict): return
 f=ensure(p); stats=p.setdefault("stats",{}); party=p.get("party","Labour")
 st.markdown("---")
 st.markdown("## 🏛️ Political strategy suite")
 st.caption("Fictional game systems—not real polling, news, demographic estimates or political forecasts.")
 tabs=st.tabs(["🗳️ Whip vs constituency","📰 Press room","📊 Polling dashboard","🏢 Department crises","♟️ Reshuffle survival"])
 with tabs[0]:
  seat,code=seat_data(p)
  a,b=st.columns([1,1])
  with a:
   st.markdown("### Your constituency profile")
   st.metric("Seat",p.get("constituency","Unknown"))
   st.caption(f"2024 boundary code: {code or p.get('constituency_code','not available')}")
   maj=seat.get("majority",seat.get("majority_votes"))
   if maj is not None: st.metric("Recorded 2024 majority",f"{int(maj):,}")
   st.warning("The GeoJSON contains boundaries and seat identifiers, not census demographics. The following are local-interest scenarios, not measured demographic facts.")
   issue=st.selectbox("Local pressure point",list(ISSUES),key="pf_issue")
   for x in ISSUES[issue]: st.write("• "+x)
  with b:
   st.markdown("### Division dilemma")
   st.write("Following the whip can help promotion prospects; rebelling may protect your local majority.")
   st.selectbox("Illustrative division",["High-speed rail route through marginal seats","Planning reform opposed by local campaigners","Tax rise funding local services","Spending restraint affecting local services"],key="pf_division")
   whip=st.radio("Party whip",["Aye","No"],horizontal=True,key="pf_whip")
   local=st.radio("Likely local preference",["Aye","No"],horizontal=True,key="pf_local")
   if st.button("Cast strategic vote",key="pf_vote",type="primary"):
    if whip==local:
     stats["party_trust"]=clamp(stats.get("party_trust",48)+4); stats["parliamentary_influence"]=clamp(stats.get("parliamentary_influence",24)+2)
     f["national"]=round(min(60,f["national"]+.3),1); msg="You followed the whip: party trust +4 and influence +2."
    else:
     stats["constituency_support"]=clamp(stats.get("constituency_support",58)+5); stats["party_trust"]=clamp(stats.get("party_trust",48)-5)
     stats["parliamentary_influence"]=clamp(stats.get("parliamentary_influence",24)-1); f["national"]=round(max(1,f["national"]-.2),1); msg="You rebelled to protect local support: constituency +5, party trust −5, influence −1."
    f["local"]=clamp(stats.get("constituency_support",58)); f["polls"].append({"Session":len(f["polls"]),"National party support":f["national"],"Constituency approval":f["local"]})
    record(p,"Whip vs constituency",msg); st.success(msg); st.rerun()
 with tabs[1]:
  st.markdown("### Anonymous briefing desk")
  st.write("Leak a fictional internal poll or rival's blunder to a political podcast. A quick profile boost comes with a hidden discovery roll.")
  for title,detail,boost,risk in LEAKS:
   with st.container(border=True):
    st.markdown("**"+title+"**"); st.write(detail); st.caption(f"Profile boost +{boost}; hidden discovery risk applies.")
    if st.button("Leak to The Rest Is Politics / The News Agents",key="pf_leak_"+str(LEAKS.index((title,detail,boost,risk)))):
     found=random.random()<min(.8,risk+int(p.get("ethics_risk",0))*.04+max(0,50-int(stats.get("integrity",78)))*.003)
     stats["public_profile"]=clamp(stats.get("public_profile",25)+boost)
     if found:
      stats["party_trust"]=clamp(stats.get("party_trust",48)-12); p["ethics_risk"]=clamp(p.get("ethics_risk",0)+1,0,5)
      msg="The source was discovered: party trust −12 and standards risk increased."
     else:
      stats["constituency_support"]=clamp(stats.get("constituency_support",58)+2); msg="The briefing stayed anonymous—for now. Public profile rose."
     f["leaks"].append({"headline":title,"outcome":msg}); record(p,"Anonymous briefing",msg); st.warning(msg) if found else st.success(msg); st.rerun()
  for item in f["leaks"][-3:]: st.caption(item["headline"]+" — "+item["outcome"])
 with tabs[2]:
  st.markdown("### National support vs constituency approval")
  st.caption("Fictional, game-only polling. Actions and crises update the series; it is not a forecast.")
  df=pd.DataFrame(f["polls"])
  fig=px.line(df,x="Session",y=["National party support","Constituency approval"],markers=True,labels={"value":"Support / approval (%)","variable":"Series"},title=f"{party}: national support and local approval")
  fig.update_layout(yaxis_range=[0,100],height=380,margin=dict(l=10,r=10,t=55,b=10),legend_title_text="")
  st.plotly_chart(fig,use_container_width=True)
  c1,c2=st.columns(2); c1.metric("National party support",f'{f["national"]:.1f}%'); c2.metric("Constituency approval",f'{f["local"]}%')
  if st.button("Run a new fictional poll",key="pf_poll"):
   f["national"]=round(max(1,min(60,f["national"]+random.uniform(-1.8,1.8))),1); f["local"]=clamp(stats.get("constituency_support",f["local"])+random.uniform(-2,2))
   f["polls"].append({"Session":len(f["polls"]),"National party support":f["national"],"Constituency approval":f["local"]}); st.rerun()
 with tabs[3]:
  st.markdown("### Departmental mini-crises")
  dep=st.selectbox("Departmental brief",DEPARTMENTS,key="pf_department")
  if dep=="Transport Secretary":
   st.write("Route a high-speed rail line through marginal constituencies while balancing cost, coverage and NIMBY backlash.")
   route=st.slider("Route ambition / coverage",1,10,6,key="pf_route"); budget=st.slider("Budget (£bn, fictional)",5,80,35,key="pf_rail_budget"); mitigation=st.slider("Noise mitigation and local transport package",0,100,45,key="pf_mitigation")
   if st.button("Submit route to Cabinet",key="pf_route_submit"):
    cost=clamp(budget+route*3-mitigation*.08); backlash=clamp(70-mitigation*.45+route*2)
    if budget>=25 and mitigation>=45:
     stats["policy_expertise"]=clamp(stats.get("policy_expertise",30)+4); stats["constituency_support"]=clamp(stats.get("constituency_support",58)-1); msg=f"Route approved. Cost pressure {cost}/100; local backlash {backlash}/100."
    else:
     stats["constituency_support"]=clamp(stats.get("constituency_support",58)-5); stats["party_trust"]=clamp(stats.get("party_trust",48)-2); msg=f"Cabinet challenged the route. Cost pressure {cost}/100; backlash {backlash}/100."
    f["local"]=clamp(stats.get("constituency_support",58)); f["polls"].append({"Session":len(f["polls"]),"National party support":f["national"],"Constituency approval":f["local"]}); record(p,"High-speed rail crisis",msg); st.info(msg); st.rerun()
  elif dep=="Chancellor":
   st.write("Balance inflation, tax and public spending ahead of a fictional Budget statement.")
   tax=st.slider("Taxation intensity",0,100,int(f["tax"]),key="pf_tax"); spend=st.slider("Public spending intensity",0,100,55,key="pf_spend")
   st.metric("Modelled inflation",f'{f["inflation"]:.1f}%')
   if st.button("Deliver Budget statement",key="pf_budget"):
    f["tax"]=tax; f["inflation"]=round(max(.5,min(12,f["inflation"]+(50-tax)*.035+(spend-50)*.025)),1)
    stats["policy_expertise"]=clamp(stats.get("policy_expertise",30)+(3 if 35<=tax<=70 else 1))
    stats["constituency_support"]=clamp(stats.get("constituency_support",58)+(2 if tax<45 else -2 if tax>75 else 0))
    f["national"]=round(max(1,min(60,f["national"]+(.4 if 35<=tax<=70 else -.4))),1); f["local"]=clamp(stats.get("constituency_support",58))
    msg=f"Budget model updated: fictional inflation {f['inflation']:.1f}%, tax pressure {tax}/100, spending {spend}/100."
    f["polls"].append({"Session":len(f["polls"]),"National party support":f["national"],"Constituency approval":f["local"]}); record(p,"Budget statement",msg); st.success(msg); st.rerun()
  else:
   effort=st.slider("Service-delivery investment / effort",0,100,60,key="pf_generic_effort")
   if st.button("Respond to departmental crisis",key="pf_generic_dept"):
    stats["policy_expertise"]=clamp(stats.get("policy_expertise",30)+(3 if effort>=50 else 1)); stats["constituency_support"]=clamp(stats.get("constituency_support",58)+(2 if effort>=65 else -2))
    f["local"]=clamp(stats.get("constituency_support",58)); f["polls"].append({"Session":len(f["polls"]),"National party support":f["national"],"Constituency approval":f["local"]})
    msg=f"{dep} delivery effort set to {effort}/100."; record(p,dep+" crisis",msg); st.success(msg); st.rerun()
 with tabs[4]:
  st.markdown("### Cabinet reshuffle survival")
  st.write("A random PM approval shock may trigger a reshuffle. Choose loyalty, resignation or a risky briefing against the PM.")
  if st.button("Generate PM approval shock",key="pf_shock"):
   f["pm_approval"]=random.randint(8,38); f["reshuffle_pending"]=True; f["reshuffle_count"]+=1
   record(p,"Downing Street crisis",f"PM's fictional approval fell to {f['pm_approval']}%; a reshuffle is under discussion."); st.rerun()
  if f.get("reshuffle_pending"):
   st.warning(f'PM approval: {f.get("pm_approval",25)}% (fictional).')
   choice=st.radio("Your move",["Pledge public loyalty","Resign on principle and trigger a leadership contest","Quietly brief against the PM for a better portfolio"],key="pf_reshuffle_choice")
   if st.button("Confirm reshuffle strategy",key="pf_reshuffle_confirm",type="primary"):
    trust=int(stats.get("party_trust",48))
    if choice=="Pledge public loyalty":
     stats["party_trust"]=clamp(trust+5); stats["parliamentary_influence"]=clamp(stats.get("parliamentary_influence",24)+2); msg="Public loyalty improved leadership confidence."
     if random.random()<.25+trust/500:
      p["role"]="Minister"; p.setdefault("promotion_log",[]).append({"role":"Minister","year":p.get("career_year",1),"term":p.get("career_term",1),"reason":"Backed PM during reshuffle"}); msg+=" You received a simulated ministerial promotion."
    elif choice.startswith("Resign"):
     stats["integrity"]=clamp(stats.get("integrity",78)+5); stats["party_trust"]=clamp(trust-8); p.setdefault("leadership_contests",[]).append({"trigger":"Resigned during reshuffle","year":p.get("career_year",1),"support":random.randint(5,30)}); msg="You resigned on principle; integrity rose and a fictional leadership contest was triggered."
    else:
     stats["public_profile"]=clamp(stats.get("public_profile",25)+6)
     if random.random()<.38:
      stats["party_trust"]=clamp(trust-15); p["ethics_risk"]=clamp(p.get("ethics_risk",0)+1,0,5); msg="Your briefing was traced: party trust −15 and standards risk increased."
     else:
      stats["party_trust"]=clamp(trust+3); p["portfolio_id"]=random.choice(["transport","treasury","health","housing","environment"]); msg="Your briefing weakened a rival and improved your portfolio prospects."
    f["reshuffle_pending"]=False; record(p,"Reshuffle survival",msg); st.success(msg); st.rerun()
  else: st.caption("No reshuffle crisis active. Generate an approval shock to test your strategy.")
