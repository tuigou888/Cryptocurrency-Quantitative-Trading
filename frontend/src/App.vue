<template>
  <div class="app-layout">
    <Sidebar :active-page="activePage" @navigate="handleNavigate" />
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import Sidebar from './components/Sidebar.vue';
import { sharedStore } from './shared/sharedStore';
import { EventBus } from './shared/eventBus';

const activePage = ref(sharedStore.get('activePage'));

function handleNavigate(page: string) {
  activePage.value = page;
  sharedStore.set('activePage', page);
  EventBus.emit('navigate', { page });
}

onMounted(() => {
  sharedStore.subscribe('activePage', (state) => {
    activePage.value = state.activePage;
  });
});
</script>
