import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';
import AuthLayout from '../layouts/AuthLayout';
import DashboardPage from '../pages/DashboardPage';
import CallingPage from '../pages/CallingPage';
import LeadsPage from '../pages/LeadsPage';
import HistoryPage from '../pages/HistoryPage';
import CallDetailsPage from '../pages/CallDetailsPage';
import AnalyticsPage from '../pages/AnalyticsPage';
import SettingsPage from '../pages/SettingsPage';
import SMSPage from '../pages/SMSPage';
import SMSConversationDetailPage from '../pages/SMSConversationDetailPage';
import PopupPage from '../pages/PopupPage';
import CampaignDashboardPage from '../pages/CampaignDashboardPage';
import PhoneNumbersPage from '../pages/PhoneNumbersPage';
import StoresPage from '../pages/StoresPage';
import LoginPage from '../pages/LoginPage';
import SignUpPage from '../pages/SignUpPage';
import NotFoundPage from '../pages/NotFoundPage';

const AppRoutes: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Protected Routes - Main Layout */}
        <Route element={<MainLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/calling" element={<CallingPage />} />
          <Route path="/leads" element={<LeadsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/history/:id" element={<CallDetailsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/sms" element={<SMSPage />} />
          <Route path="/sms/phone/:phoneNumber" element={<SMSConversationDetailPage />} />
          <Route path="/sms/:id" element={<SMSConversationDetailPage />} />
          <Route path="/popup" element={<PopupPage />} />
          <Route path="/campaigns" element={<CampaignDashboardPage />} />
          <Route path="/phone-numbers" element={<PhoneNumbersPage />} />
          <Route path="/stores" element={<StoresPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        {/* Auth Routes - Auth Layout */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignUpPage />} />
        </Route>

        {/* 404 Page */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default AppRoutes;
