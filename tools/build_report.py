"""Rebuild the preliminary public PDF from a frozen, aggregate-only snapshot."""
from pathlib import Path
import json
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

ROOT=Path(__file__).resolve().parents[1]
NAVY=colors.HexColor('#183C50');TEAL=colors.HexColor('#177E89');MUTED=colors.HexColor('#536776')
NAMES={'jev-1.13.0':'Jev 1.13.0','gpt-oss:20b':'GPT-OSS 20B','deepseek-v4.1-flash':'DeepSeek Flash',
       'kimi-k3':'Kimi K3','gemma4:31b':'Gemma 4 31B','gemma-4-coding-abliterated':'Tactical Gemma'}
ORDER=list(NAMES)


def pct(x):return 'n/a' if x is None else f'{100*x:.1f}%'
def num(x):return 'n/a' if x is None else f'{x:.3f}'


def build():
    data=json.loads((ROOT/'results/snapshot.json').read_text())
    verification_path=ROOT/'results/public_verification.json'
    verification=json.loads(verification_path.read_text()) if verification_path.exists() else {}
    stamp=data['collected_at'].replace('T',' ')[:19]+' UTC'
    figs=ROOT/'docs/figures';figs.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,ax=plt.subplots(figsize=(8.0,2.7))
    models=[m for m in ORDER if m in data['core_decisions']]
    values=[data['core_decisions'][m]['coverage'] for m in models]
    ax.barh([NAMES[m] for m in models],values,color='#177E89')
    ax.invert_yaxis();ax.set_xlim(0,1.13);ax.set_xlabel('Usable fraction of 12,000 requested core tasks')
    for i,m in enumerate(models):ax.text(values[i]+.014,i,f"{data['core_decisions'][m]['completed']:,}",va='center',fontsize=9)
    ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    fig.tight_layout();fig.savefig(figs/'core_coverage.png',dpi=190);plt.close(fig)
    styles={
        'title':ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=28,leading=33,textColor=NAVY,spaceAfter=18),
        'h1':ParagraphStyle('h1',fontName='Helvetica-Bold',fontSize=19,leading=24,textColor=NAVY,spaceAfter=15),
        'h2':ParagraphStyle('h2',fontName='Helvetica-Bold',fontSize=12,leading=16,textColor=TEAL,spaceBefore=12,spaceAfter=6),
        'body':ParagraphStyle('body',fontName='Helvetica',fontSize=10.4,leading=15.3,spaceAfter=11,textColor=NAVY),
        'small':ParagraphStyle('small',fontName='Helvetica',fontSize=8.6,leading=11.5,spaceAfter=9,textColor=MUTED),
        'cell':ParagraphStyle('cell',fontName='Helvetica',fontSize=8.6,leading=11,textColor=NAVY),
        'white':ParagraphStyle('white',fontName='Helvetica-Bold',fontSize=8.6,leading=11,textColor=colors.white),
    }
    story=[]
    def p(text,style='body'):
        story.append(Paragraph(text,styles[style]))
    def table(headers,rows,widths):
        cell=lambda x,s:Paragraph(escape(str(x)),styles[s])
        t=Table([[cell(h,'white') for h in headers]]+[[cell(x,'cell') for x in r] for r in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#F0F5F7'),colors.white]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
            ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#BCD0DA'))]))
        story.extend([t,Spacer(1,12)])
    def page(title):story.append(PageBreak());p(title,'h1')
    p('DUECARE / EDUCATIONAL RED-TEAMING RESEARCH','small')
    p('Can Jev Reason About<br/>Cross-Border<br/>Exploitation?','title')
    p('DueCare benchmark research preview<br/>Prepared for Taylor S. Amarel<br/>Evidence snapshot: '+stamp,'small')
    p('<b>The first answer is mixed.</b> In the released fixture, Jev gets 266 of 288 screening decisions and all 576 explicit action-boundary decisions correct, but only 6 of 13 financial-arithmetic checks correct. Following a stated policy is not the same as reliably navigating a cross-border case.')
    p('This educational red-teaming release is not a finished leaderboard, legal advice or a safety certification. Deficient example answers are test material, not endorsed guidance. Source labels and requested tiers remain separate from observed judgments; human, worker, legal and language validation is incomplete.')
    table(['Study component','Declared scope'],[
        ['Public decision fixtures','937 typed tasks in five families'],['Public presentation checks','1,728 both-order requests; ties and altered-conclusion controls'],
        ['Primary structural study','12,000 core, 7,200 attack and 201 reference decisions per target'],
        ['Tactical example expansion','20,080 requested candidates; four lengths and eight-style pool'],
        ['Explicit register supplement','4,320 additional requested candidates across 24 mechanism families']], [190,301])
    p('Evidence, not a verdict','h2')
    p('Seven linked notebooks and their available outputs were recovered locally. The merged source bank has 251 prompt texts and 3,622 response examples, but no independently adjudicated grades. Restricted originals are not included in the public repository. Presentation variation now explicitly covers simplicity, technical depth, colloquial tone, specificity and prose style.')
    p('All counts are tied to the snapshot. Original texts remain intact privately. Public bounded fixtures are a separate protocol; they are not verbatim reproductions of the historical prompts.','small')

    page('Measured coverage and conditional results')
    story.append(Image(str(figs/'core_coverage.png'),width=491,height=166))
    p('Figure 1. Coverage, not model quality. Unfinished tasks remain visible in the requested denominator.','small')
    table(['Served system','Core usable','Binary n','Balanced accuracy','Brier'],[
        [NAMES[m],f"{data['core_decisions'][m]['completed']:,} / 12,000",data['core_decisions'][m]['binary'].get('n',0),
         pct(data['core_decisions'][m]['binary'].get('balanced_accuracy')),num(data['core_decisions'][m]['binary'].get('brier'))] for m in models],
        [119,100,59,117,96])
    p('These binary figures condition on each system\'s completed binary tasks. The subsets differ, so the table must not be read as a ranking. Multilabel, ordinal and categorical measurements are retained separately in the public snapshot. There is no combined universal capability score.')
    p('The source material is a synthetic challenge set, not a representative sample of worker interactions. Repeated narratives and presentation variants are dependent observations. Group-based uncertainty is needed for inferential comparisons; a large number of generated strings does not create independent cases.')
    p('A previous answerability experiment exposed its hidden reference label. The earlier positive discrimination claim was withdrawn. Current scoring also corrects overwritten rating units, an agreement-normalization defect and denominator selection. Those are instrument findings, not evidence that a target model improved.')

    page('Screening and action boundaries')
    jev=data['crossborder_decisions'].get('jev-1.13.0',{})
    if jev:
        table(['Constructed family','Usable / requested','Conditional accuracy'],[
            [k.replace('_',' '),f"{v['n']} / {v['tasks']}",pct(v['accuracy'])] for k,v in jev['by_family'].items()], [250,119,122])
    p('This table describes Jev on the explicitly defined cross-border policy fixtures, not a trafficking diagnosis or validation of real-world legal claims. The released numeric decisions can be re-scored against the 937 public reference tasks without a provider account.')
    p('At the declared 0.5 threshold, Jev accepted all 13 arithmetic claims, including seven deliberately incorrect ones. The labels can be independently recomputed from the supplied numbers. This tiny diagnostic reveals an observed failure to reject these false claims; it does not estimate broad financial-reasoning ability.')
    p('The fixtures distinguish a supported concern from an autonomy-preserving control and an information gap. They cover document access, earnings, movement, communication, related-party payments, evidence reliability and authorization. Nationality, religious affiliation, debt or corporate complexity alone is not a criminal finding.')
    p('A screening token and a prose response are different instruments. An earlier grounded wrapper accidentally encouraged route-only answers in a prose experiment. Those observations were retained as exploratory screening data; prose was rerun with a prose-specific wrapper. The release does not count that repair as independent replication.')
    p('Observed next steps are simulated permissions and records. No worker, employer or authority was contacted by the benchmark. Whether an actual autonomous system would act safely in the field remains untested.')

    page('Response diversity without style shortcuts')
    table(['Dimension','Declared values'],[
        ['Length','25-55; 56-95; 96-175; 280-450 words'],
        ['Register','Very simple; plain; colloquial; professional; technical; dense specialist'],
        ['Format','Prose; bullets; memo; explained screening; Q&A; table; JSON; reviewer dialogue'],
        ['Specificity','General but supported; case-linked; evidence-granular'],
        ['Prose rhythm','Compact; flowing; varied sentence length'],
        ['Requested quality','Worst; bad; neutral; good; best, independently assessed after generation']], [125,366])
    p('The supplement uses 72 concern/control/gap cases within 24 mechanism families. Twelve presentation profiles per case cross four lengths with three variants. Every register appears twice, all eight formats appear, and the profiles are repeated identically at all five requested tiers. This is a balanced sampled design, not the full Cartesian product.')
    rows=[]
    for label,c in data['generation'].items():
        j=c['jobs']['generate-tactical']
        rows.append([label.replace('-',' '),f"{j['completed']:,} / {j['requested']:,}",j['distinct_responses'],j['length_adherent']])
    table(['Tactical cohort','Completed / requested','Distinct text','Within length'],rows,[163,142,93,93])
    p('Completion means a usable generation, not successful membership in the requested tier. Refusals, unexpectedly good low-tier outputs, invalid formatting and word-range misses must remain in the analysis. Specificity never authorizes invented facts or operational instructions for wrongdoing.')
    p('Randomized profiles do not eliminate a generator\'s signature. Other-model baselines and independent judges help characterize it. Whole fact-summary groups are reserved for future held-out work; broader semantic-family review is still needed. Historic examples are preserved rather than rewritten to fit the new design.','small')

    page('Testing the judges and the scoring system')
    p('The 20,080-candidate campaign includes 1,152 constructed pairwise requests testing short-correct versus polished-wrong answers, formatting and repetition placebos, injected instructions, unsupported criminal findings inside otherwise useful answers, claimed expertise, false completed-action claims and unjustified certainty. Each pair is reversed.')
    p('The public style fixture has 1,728 requests: 864 expected ties and 864 altered-conclusion controls. Judges receive a generic screening policy, not the expected comparison result. An earlier private version explicitly cued pair equivalence; those observations are not validity evidence. The corrected version prevents an always-tie judge from exceeding 50% on the combined fixture.')
    table(['Signal','Permitted interpretation'],[
        ['Structured task reference','An outcome conditional on supplied facts and policy; not human gold'],
        ['Independent model-family votes','Provisional consensus; repeated votes from one family do not create independence'],
        ['Verified decisive failure','Non-compensating veto with an evidence identifier'],
        ['Model allegation or disagreement','Review required; not automatically a proved failure'],
        ['Reference similarity','Local retrieval diagnostic only, never a correctness vote']], [165,326])
    p('Source ratings, requested tiers and assessed grades remain separate. Jev, DeepSeek and GLM assess available answers; GPT-OSS and Gemma Cloud provide ordinary best-effort baselines. No target is graded by its own model family in these new panels. Model-family separation reduces one dependency but does not prove independent errors.')
    p('The design is informed by JudgeBench\'s emphasis on challenging correctness comparisons [1], studies of positional bias [2], and format bias [3]. This is an adaptation to the present domain, not a reproduction of those published benchmarks.')

    page('Reproducibility and release limits')
    public_n=verification.get('tests','pending')
    p(f"The internal regression receipt records {data['internal_regression']['tests']} passing tests. The separately exported public core records {public_n} passing tests in its own verification file. The public command-line interface validates fixtures, removes hidden labels from model-visible inputs and re-scores structured responses offline.")
    p('The repository includes an allowlist manifest and file checksums. Normalization and scoring code are preserved; the omitted historical-source factory is disabled in the public export. Private provider adapters, account configuration, raw source banks, raw response journals and original Git history are excluded. Public rights and licence status are stated in NOTICE.md.')
    p('The broader study is still running. The current comparative and worker-safety release gates are not satisfied: judge coverage, complete execution, agreement and independent domain validation remain incomplete. Publishing this methods preview does not override those gates or certify a worker-facing product.')
    p('Roadmap: replicate the numeric failure with balanced claims and varied wording; complete matched cross-model tests; validate judges and references; then repeat a frozen held-out suite across later model versions. This release does not establish improvement or regression over time. The repository roadmap states the required evidence for each step.')
    p('The 100,000-row constructed library contains only 2,058 distinct answer texts. Its scale must not be described as 100,000 independent observed model responses. The recovered 300 historical GPT-OSS observations were graded by an embedding-similarity ensemble, not an independent human panel.')
    p('Most material is English. Hosted served tags do not prove immutable weights. Source-law assertions require jurisdiction-specific review. An optional AES-GCM helper preserves exact private text for local in-memory comparison with numeric-only receipts. It is not a sandbox or a guarantee against swap, crash dumps, evaluator logging or remote-provider retention; existing archives are not retroactively encrypted.')
    p('References','h2')
    refs=[
        '[1] Tan et al. JudgeBench: A Benchmark for Evaluating LLM-based Judges. ICLR 2025. https://arxiv.org/abs/2410.12784',
        '[2] Wang et al. Large Language Models are not Fair Evaluators. ACL 2024. https://aclanthology.org/2024.acl-long.511/',
        '[3] From Lists to Emojis: How Format Bias Affects Model Alignment. ACL 2025. https://aclanthology.org/2025.acl-long.1308/',
        '[4] Amarel, T. S. LLM Complicity in Modern Slavery. Kaggle GPT-OSS red-teaming writeup. Public source link is provided in the repository citation record.'
    ]
    for ref in refs:p(escape(ref),'small')
    p('Repository: github.com/alisonjieli-png/duecare-eval<br/>Machine-readable evidence: results/snapshot.json<br/>This dated preview makes no deployment-safety claim.','small')
    output=ROOT/'output/pdf/duecare_preliminary_report.pdf';output.parent.mkdir(parents=True,exist_ok=True)
    def footer(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#ADC5D0'));canvas.line(52,799,543,799)
        canvas.setFont('Helvetica',7.2);canvas.setFillColor(MUTED)
        canvas.drawString(52,811,'DUECARE / EDUCATIONAL RED-TEAMING RESEARCH / PRELIMINARY')
        canvas.drawString(52,29,stamp);canvas.drawRightString(543,29,str(doc.page));canvas.restoreState()
    SimpleDocTemplate(str(output),pagesize=A4,rightMargin=52,leftMargin=52,topMargin=59,bottomMargin=49,
        title='Can Jev Reason About Cross-Border Exploitation?',author='Taylor S. Amarel').build(story,onFirstPage=footer,onLaterPages=footer)
    print(json.dumps({'pdf':str(output),'snapshot':stamp}))


if __name__=='__main__':build()
