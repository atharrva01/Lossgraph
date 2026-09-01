'use client'

import React from 'react'
import Link from 'next/link'
import {
  ArrowLeft, ArrowRight, Bot, Brain, Clock, GitBranch, Network,
  Receipt, Scale, ShieldCheck,
} from 'lucide-react'
import { DashboardLayout } from '@/components/DashboardLayout'

function StepCard({
  number, icon: Icon, title, children,
}: {
  number: number
  icon: React.ElementType
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center shrink-0">
        <div className="w-9 h-9 rounded-full bg-gray-900 text-white flex items-center justify-center text-sm font-bold">
          {number}
        </div>
        <div className="w-px flex-1 bg-gray-200 my-2" />
      </div>
      <div className="pb-8">
        <div className="flex items-center gap-2 mb-1">
          <Icon className="w-4 h-4 text-gray-500" />
          <h3 className="text-base font-bold text-gray-900">{title}</h3>
        </div>
        <div className="text-sm text-gray-600 leading-relaxed">{children}</div>
      </div>
    </div>
  )
}

export default function HowItWorksPage() {
  return (
    <DashboardLayout>
      <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to Command Center
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-2">How LossGraph Works</h1>
      <p className="text-sm text-gray-600 mb-8 max-w-3xl">
        Most fraud tools score one transaction in isolation. LossGraph instead asks whether the merchant
        is entering a <strong>Loss Event</strong> -- a coordinated pattern across customers, devices, and
        time -- and works out the cheapest effective way to stop it. Everything on this page reflects the
        actual pipeline: <code className="bg-gray-100 px-1 rounded text-xs">data/generation/</code> and{' '}
        <code className="bg-gray-100 px-1 rounded text-xs">ml/</code> in the repo, not a mockup.
      </p>

      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-10">
        <StepCard number={1} icon={Network} title="Three engines look at the same data from different angles">
          <p className="mb-2">
            Every transaction is scored three separate ways, and each engine deliberately sees something
            the others cannot:
          </p>
          <ul className="space-y-1.5 ml-1">
            <li><strong>Transaction risk model</strong> (LightGBM) -- catches obvious fraud at the moment of
              purchase (odd hour, thin history, high amount). Catches ~100% of card-testing-style fraud,
              but ~0% of chargebacks on transactions that looked completely normal when they happened.</li>
            <li><strong>Entity graph engine</strong> (NetworkX) -- builds a network of which customers share
              a device or delivery address, and scores how suspicious that cluster's behavior looks
              (return rate, how bursty the activity was). Scores 0 for anyone not in a cluster.</li>
            <li><strong>Temporal anomaly engine</strong> -- watches each merchant's daily return/dispute rate
              against its own recent baseline. This is the <em>only</em> one of the three that can catch a
              chargeback wave, since disputes surface weeks after the order.</li>
          </ul>
        </StepCard>

        <StepCard number={2} icon={Brain} title="The three scores are fused, not averaged">
          <p>
            <code className="bg-gray-100 px-1 rounded text-xs">P_fused = 1 - (1-P₁)(1-P₂)(1-P₃)</code> --
            any single engine being confident is enough to raise the fused score, while it only stays low
            if all three independently see nothing. This is what the <strong>"How the confidence score was
            computed"</strong> panel on every incident page shows you directly: which engine actually drove
            the number, not just the final result.
          </p>
        </StepCard>

        <StepCard number={3} icon={GitBranch} title="A Loss Event is formed -- not a flagged transaction">
          <p>
            Transactions whose fused scores cluster together (a coordinated group of accounts) or a
            merchant-day whose outcome rate spiked get bundled into one <strong>Loss Event</strong>, with a
            structured evidence chain (each claim tagged E1, E2, ... and traceable to a real number) and an
            overall confidence.
          </p>
        </StepCard>

        <StepCard number={4} icon={Scale} title="A counterfactual simulator picks the cheapest effective action">
          <p className="mb-2">
            For every event, six possible actions (allow, monitor, verify, hold, block, investigate cluster)
            are simulated using the merchant's own cost numbers -- what a false positive costs them, what
            verification costs, what a lost sale costs. Whichever has the highest net Rupee benefit is
            recommended. A low-confidence event and a high-confidence event get genuinely different
            recommendations, not the same threshold-based cutoff.
          </p>
        </StepCard>

        <StepCard number={5} icon={Bot} title="An AI investigator writes the case file">
          <p>
            Gemini turns the evidence chain into a plain-English summary -- but it only narrates evidence
            that already exists; it cannot invent a claim, see the ground-truth answer, or recommend a
            different action than the one already chosen. Every sentence has to cite a real evidence ID or
            it's rejected and replaced with a template before it reaches this page.
          </p>
        </StepCard>

        <StepCard number={6} icon={Receipt} title="A later chargeback links straight back">
          <p>
            When a dispute arrives, the system checks whether it already knows something about that
            transaction instead of treating it as a fresh case. If the transaction was already part of a
            high-confidence Loss Event, the recommendation is to <strong>accept</strong> the chargeback, not
            contest it -- contesting would mean arguing against the system's own earlier finding.
          </p>
        </StepCard>

        <div className="flex gap-4">
          <div className="flex flex-col items-center shrink-0">
            <div className="w-9 h-9 rounded-full bg-green-600 text-white flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div>
            <h3 className="text-base font-bold text-gray-900 mb-1">That's the whole loop</h3>
            <p className="text-sm text-gray-600">
              Detect → explain → decide → respond → close the loop when a dispute confirms it. Nothing on
              this page is narrated over a mockup -- click through to any incident to see the real numbers.
            </p>
          </div>
        </div>
      </div>

      <div className="bg-gray-900 text-white rounded-lg p-6 mb-10">
        <h2 className="text-lg font-bold mb-4">The honest numbers (held-out test split)</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-2xl font-bold">0.61</p>
            <p className="text-xs text-gray-400 mt-1">Fused PR-AUC -- beats every single engine alone</p>
          </div>
          <div>
            <p className="text-2xl font-bold">79%</p>
            <p className="text-xs text-gray-400 mt-1">Gross loss prevented at the economically-tuned threshold</p>
          </div>
          <div>
            <p className="text-2xl font-bold">4.71 vs 0.70</p>
            <p className="text-xs text-gray-400 mt-1">
              Action aggressiveness (0=allow..5=block) for real-loss vs. false-alarm events -- calibrated
              from confidence alone, never from the label
            </p>
          </div>
          <div>
            <p className="text-2xl font-bold">100%</p>
            <p className="text-xs text-gray-400 mt-1">
              Of "accept this chargeback" recommendations were correct against ground truth (74/74)
            </p>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-5 flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" /> From the current <code className="bg-gray-800 px-1 rounded">make pipeline</code> run.
          Full methodology and honestly-stated limitations in <code className="bg-gray-800 px-1 rounded">docs/EVALUATION.md</code>.
        </p>
      </div>

      <div className="flex justify-center mb-4">
        <Link
          href="/"
          className="inline-flex items-center gap-2 bg-gray-900 text-white text-sm font-medium px-5 py-2.5 rounded-lg hover:bg-gray-800"
        >
          See it on real data <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </DashboardLayout>
  )
}
