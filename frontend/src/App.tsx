import { Routes, Route, Navigate } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import AppLayout from './components/layout/AppLayout';
import { LoadingSpinner } from './components/common/LoadingSpinner';

// Lazy load pages for code splitting
const DashboardPage = lazy(() => import('./pages/Dashboard/DashboardPage'));
const AgentsPage = lazy(() => import('./pages/Agents/AgentsPage'));
const AgentDetailsPage = lazy(() => import('./pages/Agents/AgentDetailsPage'));
const TasksPage = lazy(() => import('./pages/Tasks/TasksPage'));
const TaskDetailsPage = lazy(() => import('./pages/Tasks/TaskDetailsPage'));
const MonitoringPage = lazy(() => import('./pages/Monitoring/MonitoringPage'));
const SettingsPage = lazy(() => import('./pages/Settings/SettingsPage'));

function App() {
  return (
    <AppLayout>
      <Suspense fallback={<LoadingSpinner fullScreen />}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard\" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/agents/:agentId" element={<AgentDetailsPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/tasks/:taskId" element={<TaskDetailsPage />} />
          <Route path="/monitoring" element={<MonitoringPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </AppLayout>
  );
}

export default App;
