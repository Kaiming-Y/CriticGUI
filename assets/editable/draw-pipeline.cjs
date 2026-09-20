const PptxGenJS=require(process.env.PPTXGENJS_PATH||'pptxgenjs');
const path=require('path');const p=new PptxGenJS();p.defineLayout({name:'pipeline',width:18,height:8});p.layout='pipeline';const s=p.addSlide(),S=p.ShapeType;s.background={color:'FAFBFD'};
const blue='376FA8',green='2B877B',red='B95F55',ink='25364C',muted='63768B';
function box(x,y,w,h,fill='FFFFFF',stroke='D6E0EB'){s.addShape(S.roundRect,{x,y,w,h,radius:.1,rectRadius:.1,line:{color:stroke,width:1.1},fill:{color:fill}})}
function text(x,y,w,h,t,sz=16,c=ink,b=false){s.addText(t,{x,y,w,h,fontFace:'Arial',fontSize:sz,color:c,bold:b,margin:0,valign:'mid'})}
function ln(x,y,w,h=0,c=muted,arrow=false){s.addShape(S.line,{x,y,w,h,line:{color:c,width:1.8,...arrow?{endArrowType:'triangle'}:{}}})}
function step(x,y,n,title,c=blue,w=2.55){s.addShape(S.ellipse,{x,y:y+.02,w:.32,h:.32,line:{color:c},fill:{color:c}});s.addText(String(n),{x,y:y+.02,w:.32,h:.32,fontFace:'Arial',fontSize:14,color:'FFFFFF',bold:true,align:'center',valign:'mid',margin:0});text(x+.43,y,w-.43,.39,title,18,c,true)}
function check(x,y,c=green){ln(x,y,.09,.09,c);ln(x+.09,y+.09,.18,-.23,c)}
function screen(x,y,w,h,label,filled=false){box(x,y,w,h,'FFFFFF','ACC2D6');ln(x+.04,y+.17,w-.08,0,'BCCBD9');text(x+.09,y+.025,w-.18,.12,'•••',9,muted);box(x+.12,y+.36,w-.24,.29,filled?'E6F3EF':'F2F5F9',filled?green:'D6E0EB');text(x+.17,y+.4,w-.34,.18,label,11,filled?green:muted)}
text(.4,.27,17.2,.48,'CriticGUI benchmark construction from human demonstrations',27,ink,true);
text(.4,.9,17.1,.38,'Evaluate whether an action is appropriate for its instruction and the actual GUI state.',18,muted);
// Three equal preparation columns.
for(const x of [.4,3.43,6.46])box(x,1.7,2.63,5.46);
step(.58,1.92,1,'Review the plan');step(3.61,1.92,2,'Record a demo');step(6.64,1.92,3,'Align each step');
text(.63,2.52,2.15,.65,'Query + initial screen\n→ MLLM draft',16,muted);
box(.7,3.37,2.03,.43,'EEF3FB');text(.82,3.42,1.8,.30,'High · task goal',14,blue,true);
box(.85,3.99,1.88,.43,'F0EDFA');text(.97,4.04,1.6,.30,'Low · subtask',14,'7663A0',true);
box(1,4.61,1.73,.43,'EAF6F1');text(1.12,4.66,1.49,.30,'Atomic · interaction',12,green,true);
ln(.8,3.8,0,.39);ln(.8,4.19,.05);ln(.94,4.42,0,.4);ln(.94,4.82,.06);check(2.27,5.52);
text(.64,5.9,2.16,.87,'Human correction fixes\nthe order, details and\nsemantic granularity.',15);
// Human icon and recorded desktop.
s.addShape(S.ellipse,{x:3.76,y:2.67,w:.4,h:.4,line:{color:blue,width:1.5},fill:{color:'EEF3FB'}});box(3.65,3.12,.62,.61,'EEF3FB','8BAFCB');
screen(4.48,2.65,1.24,1.12,'');s.addShape(S.ellipse,{x:4.97,y:3.05,w:.13,h:.13,line:{color:red},fill:{color:red}});
ln(4.30,3.26,.13,0,blue,true);
text(3.67,4.12,2.12,.65,'Follow each atomic step.\nKeep all three levels visible.',15);
text(3.67,5.24,2.12,1.26,'Capture input events,\nbefore/after screenshots\nand action video.',15);
// Before / action / after schema with visual content.
screen(6.70,2.65,2.13,.91,'Before: empty');
ln(7.76,3.66,0,.3,blue,true);
text(6.77,4.02,1.97,.52,'Type “GUICritic”',16,blue,true);
ln(7.76,4.64,0,.3,blue,true);
screen(6.70,5.03,2.13,.91,'After: GUICritic',true);
text(6.70,6.27,2.13,.52,'Instruction + action\n+ state transition',15,muted);
ln(3.08,4.3,.29,0,blue,true);ln(6.11,4.3,.29,0,blue,true);
// Split into candidate pools.
ln(9.13,4.3,.24,0);ln(9.37,2.8,0,3.02);ln(9.37,2.8,.28,0,blue,true);ln(9.37,5.82,.28,0,red,true);
box(9.70,1.7,4.65,2.34,'F0F5FE','ADC7E7');step(9.91,1.92,4,'Positive candidates',blue,4.23);
check(10.07,2.83,blue);text(10.5,2.6,3.6,.62,'Correct demonstrations\nwith aligned evidence',17,blue,true);
text(9.94,3.42,4.15,.36,'Explain why the intended step succeeded.',15);
box(9.70,4.27,4.65,2.89,'FFF6F3','E3BCB6');step(9.91,4.49,5,'Negative candidates',red,4.23);
const rows=[['Starting state','Behind, incomplete, or already finished'],['Action / outcome','Wrong target, partial or imprecise result'],['Step alignment','Instruction and action no longer match']];
rows.forEach(([a,b],i)=>{let y=5.12+i*.59;text(9.95,y,3.95,.25,a,14,red,true);text(9.95,y+.28,4.13,.25,b,13,ink)});
// Merge then review: neither branch bypasses human label review.
ln(14.39,2.8,.28,0,blue);ln(14.67,2.8,0,3.02);ln(14.39,5.82,.28,0,red);ln(14.67,4.3,.26,0,muted,true);
box(15,1.7,2.60,5.46);step(15.20,1.92,6,'Review & assemble',blue,2.23);
text(15.22,2.73,2.16,.83,'Draft reasons with an MLLM.\nVerify with a human.',14,blue,true);
check(15.37,3.9);text(15.78,3.68,1.58,.4,'Label + reason',15,green,true);
ln(16.3,4.27,0,.36,green,true);
box(15.22,4.84,2.16,1.56,'EEF4FB');text(15.40,5.01,1.8,.28,'Critic example',17,blue,true);text(15.40,5.43,1.8,.72,'Instruction · action\nvisual evidence\njudgment · reason',13);
text(15.22,6.60,2.15,.24,'Benchmark dataset',15,blue,true);
text(.4,7.46,17.2,.29,'Construction design from research notes. Perturbations require re-evaluation: a changed or repeated action is not automatically a negative.',13,muted);
p.writeFile({fileName:path.join(__dirname,'criticgui-benchmark-pipeline.pptx')});
