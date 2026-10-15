import React from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Footer } from './Footer';
import { Toast } from '../ui/Toast';
import { useCart } from '../../context/CartContext';
import './Layout.css';

export const Layout: React.FC = () => {
  const { toast, clearToast } = useCart();

  return (
    <div className="layout">
      <Header />
      <main className="layout__main">
        <Outlet />
      </main>
      <Footer />
      <Toast toast={toast} onClose={clearToast} />
    </div>
  );
};
