<script setup lang="ts">
import { onMounted } from "vue";

import AnalysisInputPanel from "@/components/AnalysisInputPanel.vue";
import AppShell from "@/components/AppShell.vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import SidebarNav from "@/components/SidebarNav.vue";
import SkillWorkbenchPanel from "@/components/SkillWorkbenchPanel.vue";
import WelcomeState from "@/components/WelcomeState.vue";
import WorkspaceLayout from "@/components/WorkspaceLayout.vue";
import ReportPage from "@/components/report/ReportPage.vue";
import { useWorkspace } from "@/composables/useWorkspace";

const {
  form,
  status,
  cacheClearing,
  uploading,
  busy,
  canUpload,
  notice,
  report,
  history,
  health,
  skillCatalog,
  promptTemplates,
  currentTemplate,
  uploadedDocuments,
  uploadCapabilities,
  uploadQueue,
  sidebarOpen,
  sidebarCollapsed,
  errorMessage,
  lastAction,
  canSubmit,
  currentPdfUrl,
  bootstrap,
  analyze,
  uploadFiles,
  openReport,
  retry,
  clearHistory,
  clearSystemCache,
  newAnalysis,
  clearInputs,
  fillExample,
  selectTemplate,
  applyActiveTemplate,
  toggleSidebar,
  closeSidebar,
  toggleSidebarCollapse,
} = useWorkspace();

onMounted(() => {
  void bootstrap();
});
</script>

<template>
  <AppShell
    :sidebar-open="sidebarOpen"
    :sidebar-collapsed="sidebarCollapsed"
    @toggle-sidebar="toggleSidebar"
    @close-sidebar="closeSidebar"
  >
    <template #sidebar>
      <SidebarNav
        :form="form"
        :status="status"
        :busy="busy"
        :cache-clearing="cacheClearing"
        :report="report"
        :history="history"
        :health="health"
        :skill-catalog="skillCatalog"
        :collapsed="sidebarCollapsed"
        @new-analysis="newAnalysis"
        @fill-example="fillExample"
        @clear-inputs="clearInputs"
        @clear-history="clearHistory"
        @select-report="openReport"
        @close-sidebar="closeSidebar"
        @toggle-collapse="toggleSidebarCollapse"
      />
    </template>

    <WorkspaceLayout>
      <template #intro>
        <WelcomeState v-if="!report && status === 'idle'" />
        <AnalysisInputPanel
          :prompt-templates="promptTemplates"
          :active-template-id="form.templateId"
          :current-template="currentTemplate"
          :material-type="form.materialType"
          :company-code="form.companyCode"
          :query="form.query"
          :preference-note="form.preferenceNote"
          :top-k="form.topK"
          :uploaded-documents="uploadedDocuments"
          :upload-capabilities="uploadCapabilities"
          :upload-queue="uploadQueue"
          :disabled="busy"
          :uploading="uploading"
          :can-upload="canUpload"
          :submitting="status === 'loading'"
          :cache-clearing="cacheClearing"
          :can-submit="canSubmit"
          :notice-message="notice?.message"
          :notice-tone="notice?.tone"
          @update:material-type="form.materialType = $event"
          @update:company-code="form.companyCode = $event"
          @update:query="form.query = $event"
          @update:preference-note="form.preferenceNote = $event"
          @update:top-k="form.topK = $event"
          @upload-files="uploadFiles"
          @select-template="selectTemplate"
          @apply-template="applyActiveTemplate"
          @submit="analyze"
          @fill-example="fillExample"
          @clear="clearInputs"
          @clear-cache="clearSystemCache"
        />
      </template>

      <template #status>
        <LoadingState v-if="status === 'loading'" />
        <ErrorState
          v-if="errorMessage"
          :message="errorMessage"
          :has-retry="Boolean(lastAction) && !cacheClearing"
          @retry="retry"
        />
      </template>

      <template #content>
        <SkillWorkbenchPanel
          v-if="report"
          :report="report"
          :skill-catalog="skillCatalog"
        />
        <ReportPage
          v-if="report"
          :report="report"
          :pdf-url="currentPdfUrl"
        />
      </template>
    </WorkspaceLayout>
  </AppShell>
</template>
