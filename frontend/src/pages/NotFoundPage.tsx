import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, ShoppingBag } from 'lucide-react';
import { Button } from '../components/ui/Button';
import './NotFoundPage.css';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  useEffect(() => {
    document.title = '404 Page Not Found | AdesHub';
  }, []);

  return (
    <div className="not-found-page">
      <div className="container not-found-page__inner">
        <div className="not-found-badge">404 Error</div>
        <h1 className="heading-xl not-found-title">Page Not Found</h1>
        <p className="not-found-message">
          The page or product category you are looking for does not exist, has been moved, or is temporarily unavailable.
        </p>

        <div className="not-found-actions">
          <Button
            variant="primary"
            size="lg"
            onClick={() => navigate('/')}
            icon={<Home size={18} />}
          >
            Back to Homepage
          </Button>

          <Button
            variant="outline"
            size="lg"
            onClick={() => navigate('/shop')}
            icon={<ShoppingBag size={18} />}
          >
            Explore Shop Catalog
          </Button>
        </div>
      </div>
    </div>
  );
};
