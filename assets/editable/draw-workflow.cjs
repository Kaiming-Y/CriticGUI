const pptxgen = require(process.env.PPTXGENJS_PATH || 'pptxgenjs');
const path = require('path');
const pptx = new pptxgen();pptx.defineLayout({name:'flow',width:16,height:7.25});pptx.layout='flow';
const s=pptx.addSlide(), S=pptx.ShapeType;
s.background={color:'F8FAFC'};
function box(x,y,w,h,fill='FFFFFF',line='D9E2EC',r=true){s.addShape(r?S.roundRect:S.rect,{x,y,w,h,radius:.1,rectRadius:.1,fill:{color:fill},line:{color:line,width:1}})}
function text(x,y,w,h,t,size=17,color='23354B',bold=false){s.addText(t,{x,y,w,h,fontFace:'Arial',fontSize:size,color,bold,margin:0,breakLine:false,valign:'mid'})}
function line(x,y,w,h=0,color='869AAF',arrow=false){s.addShape(S.line,{x,y,w,h,line:{color,width:1.8,...(arrow?{endArrowType:'triangle'}:{})}})}
function screen(x,y,w=2.05,h=1.13){box(x,y,w,h,'FFFFFF','B3C7D8');line(x+.05,y+.19,w-.1);for(let i=0;i<3;i++)s.addShape(S.ellipse,{x:x+.1+i*.09,y:y+.075,w:.035,h:.035,line:{color:'8B9EB0'},fill:{color:'8B9EB0'}})}
function check(x,y,color='258575'){line(x,y,.10,.1,color);line(x+.10,y+.1,.20,-.25,color)}
text(.4,.25,15.2,.48,'Beyond what an agent can already execute',31,'23354B',true);
text(.4,.89,15.2,.5,'Human demonstrations extend task coverage; controlled mistakes expose difficult critic judgments.',19,'62768B');
const xs=[.4,3.52,6.64,9.76,12.88], titles=['Draft a plan','Refine & freeze','Demonstrate','Perturb','Review & package'];
const colors=['3978B1','7062A7','258575','B27937','3978B1'];
xs.forEach((x,i)=>{box(x,1.68,2.72,3.91);text(x+.18,1.87,2.35,.36,`${i+1}  ${titles[i]}`,17,colors[i],true);if(i<4)line(x+2.78,3.35,.27,0,'8498AD',true)});
// Query + observed interface become a model draft.
box(.65,2.49,2.2,.43,'EDF3FE');text(.77,2.52,1.96,.33,'Query + initial screen',14,'3978B1');
line(1.75,2.99,0,.27,'3978B1',true);box(.87,3.32,1.75,.67,'EDF3FE');text(1,3.43,1.49,.38,'MLLM draft',18,'3978B1',true);
text(.64,4.35,2.22,.85,'Propose a procedure.\nA model draft is not\nground truth.',14);
// A visible hierarchy with a human check, rather than three generic rectangles.
const levels=[['High: milestone',3.77,2.48],['Low: subtask',3.94,2.99],['Atomic: interaction',4.11,3.5]];
levels.forEach(([t,x,y],i)=>{box(x,y,1.93,.38,['F0ECFA','ECF3FB','E8F5EE'][i]);text(x+.1,y+.05,1.75,.26,t,13,colors[1]);if(i<2)line(x+.09,y+.4,0,.2,'B7ABC9')});check(5.62,4.13,'7062A7');
text(3.76,4.4,2.23,.95,'Correct the sequence.\nSplit non-atomic steps.\nKeep all three levels.',14);
// Actual desktop interaction visual.
screen(6.97,2.56);box(7.16,3.05,1.18,.30,'EDF8F4','258575');text(7.26,3.08,1,.2,'GUICritic',12,'258575');
s.addShape(S.chevron,{x:8.42,y:3.36,w:.24,h:.36,rotate:135,line:{color:'258575'},fill:{color:'258575'}});
text(6.94,3.91,2.13,.24,'Before → action → after',13,'258575',true);
text(6.88,4.4,2.23,.95,'Execute one atomic step.\nRecord input events,\nscreenshots and video.',14);
// Controlled contrast: intended target vs wrong target, same instruction.
screen(10.09,2.49);text(10.2,2.77,1.85,.24,'Same instruction',13,'B27937');
box(10.28,3.18,.65,.26,'ECF6EF','258575');box(11.16,3.18,.65,.26,'FBEDE8','B76555');
check(10.49,3.75);line(11.36,3.57,.19,.19,'B76555');line(11.55,3.57,-.19,.19,'B76555');
text(10,4.4,2.24,.95,'Restore the start state.\nIntroduce a deliberate\nerror and record again.',14);
// Review labels then package evidence.
box(13.13,2.49,2.2,.62,'EAF6EF');text(13.26,2.60,1.94,.37,'Judgment + reason',14,'258575',true);
box(13.25,3.38,1.95,.65,'EDF3FE');text(13.37,3.48,1.71,.44,'Critic examples',15,'3978B1',true);
text(13.12,4.4,2.23,.95,'Check observed outcomes.\nKeep the plan, actions\nand visual evidence.',14);
// Complementary collection path.
box(.4,5.95,10.85,.78,'EEF2F8');text(.62,6.08,10.3,.49,'Complementary source: WorldGUI agent exploration → naturally occurring successes and failures',16,'526C87');
line(11.35,6.34,2.92,0,'8498AD');line(14.27,6.34,0,-.62,'8498AD',true);
text(.4,6.94,15.2,.18,'Perturbation and final judgment are human-reviewed steps; a negative attempt is not automatically a failure label.',11,'62768B');
pptx.writeFile({fileName:path.join(__dirname,'human-demonstration-workflow.pptx')});
