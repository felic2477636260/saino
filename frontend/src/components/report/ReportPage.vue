<script setup lang="ts">
import { computed } from "vue";

import EvidenceSection from "@/components/report/EvidenceSection.vue";
import FindingsSection from "@/components/report/FindingsSection.vue";
import RecommendationsSection from "@/components/report/RecommendationsSection.vue";
import ReportBodySection from "@/components/report/ReportBodySection.vue";
import ReportHeader from "@/components/report/ReportHeader.vue";
import ReportOverviewPanel from "@/components/report/ReportOverviewPanel.vue";
import RiskOpportunitySection from "@/components/report/RiskOpportunitySection.vue";
import ScoreSection from "@/components/report/ScoreSection.vue";
import SkillTraceSection from "@/components/report/SkillTraceSection.vue";
import VerificationSection from "@/components/report/VerificationSection.vue";
import {
  getActionItems,
  getKeyEvidence,
  getKeyJudgments,
  getNextSteps,
  getRiskOpportunities,
  getVerificationFocus,
} from "@/lib/report";
import type { ReportDetailResponse, SkillCatalog } from "@/types/api";

const props = defineProps<{
  report: ReportDetailResponse;
  skillCatalog: SkillCatalog;
  pdfUrl: string;
}>();

const judgments = computed(() => getKeyJudgments(props.report));
const riskOpportunities = computed(() => getRiskOpportunities(props.report));
const nextSteps = computed(() => getNextSteps(props.report));
const actionItems = computed(() => getActionItems(props.report));
const keyEvidence = computed(() => getKeyEvidence(props.report));
const verificationFocus = computed(() => getVerificationFocus(props.report));
</script>

<template>
  <section class="report-page">
    <ReportHeader :report="report" :pdf-url="pdfUrl" />

    <div class="report-page__layout">
      <ReportOverviewPanel>
        <ScoreSection :report="report" />
        <FindingsSection :judgments="judgments" />
        <RiskOpportunitySection
          :risks="riskOpportunities.risks"
          :opportunities="riskOpportunities.opportunities"
        />
        <RecommendationsSection :actions="actionItems" :recommendations="nextSteps" />
        <VerificationSection :verification-notes="verificationFocus" />
        <EvidenceSection :evidence="keyEvidence" />
        <SkillTraceSection :report="report" :skill-catalog="skillCatalog" />
      </ReportOverviewPanel>

      <ReportBodySection :report="report" />
    </div>
  </section>
</template>
