// Auth Layout - Simple pass-through for login/signup pages

import React from 'react';
import { Outlet } from 'react-router-dom';

const AuthLayout: React.FC = () => {
  return <Outlet />;
};

export default AuthLayout;
