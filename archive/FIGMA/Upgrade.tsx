import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { loadSubscription, upgradeSubscription } from '../utils/storage';
import type { SubscriptionTier, UserSubscription } from '../types';
import { Check, Crown, Zap, Star } from 'lucide-react';

export function Upgrade() {
  const navigate = useNavigate();
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);

  useEffect(() => {
    setSubscription(loadSubscription());
  }, []);

  const handleUpgrade = (tier: SubscriptionTier) => {
    upgradeSubscription(tier);
    setSubscription(loadSubscription());
    // In a real app, this would integrate with a payment processor
    setTimeout(() => {
      navigate('/dashboard');
    }, 1000);
  };

  const plans = [
    {
      name: 'Free',
      tier: 'free' as SubscriptionTier,
      price: '$0',
      period: 'forever',
      icon: Star,
      color: 'bg-slate-500',
      features: [
        '5 cases per day',
        'Beginner & Intermediate levels',
        'Basic progress tracking',
        'Achievement badges',
      ],
      limitations: [
        'No leaderboard access',
        'No expert level',
        'Limited daily cases',
      ],
    },
    {
      name: 'Premium',
      tier: 'premium' as SubscriptionTier,
      price: '$9.99',
      period: 'per month',
      icon: Zap,
      color: 'bg-blue-500',
      features: [
        '20 cases per day',
        'All difficulty levels except Master',
        'Global leaderboard access',
        'Detailed analytics',
        'Priority support',
        'All achievement badges',
      ],
      limitations: ['No master level cases'],
      popular: true,
    },
    {
      name: 'Pro',
      tier: 'pro' as SubscriptionTier,
      price: '$19.99',
      period: 'per month',
      icon: Crown,
      color: 'bg-gradient-to-r from-amber-500 to-orange-500',
      features: [
        'Unlimited cases',
        'All difficulty levels including Master',
        'Global leaderboard access',
        'Advanced analytics & insights',
        'Priority support',
        'Exclusive badges',
        'Custom case generation',
        'Downloadable reports',
      ],
      limitations: [],
    },
  ];

  if (!subscription) return null;

  return (
    <div className="container mx-auto p-6 max-w-7xl space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-4xl font-bold">Choose Your Plan</h1>
        <p className="text-lg text-muted-foreground">
          Unlock advanced features and accelerate your ABG mastery
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        {plans.map((plan) => {
          const IconComponent = plan.icon;
          const isCurrentPlan = subscription.tier === plan.tier;

          return (
            <Card
              key={plan.name}
              className={`relative ${
                plan.popular
                  ? 'border-2 border-primary shadow-lg scale-105'
                  : 'border'
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <div className="bg-primary text-primary-foreground px-4 py-1 rounded-full text-sm font-bold">
                    MOST POPULAR
                  </div>
                </div>
              )}

              <CardHeader className="text-center pb-4">
                <div
                  className={`w-16 h-16 mx-auto rounded-full ${plan.color} flex items-center justify-center mb-4`}
                >
                  <IconComponent className="w-8 h-8 text-white" />
                </div>
                <CardTitle className="text-2xl">{plan.name}</CardTitle>
                <CardDescription>
                  <div className="text-3xl font-bold text-foreground mt-2">
                    {plan.price}
                  </div>
                  <div className="text-sm">{plan.period}</div>
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-6">
                <div className="space-y-3">
                  {plan.features.map((feature, index) => (
                    <div key={index} className="flex items-start gap-2">
                      <Check className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                      <span className="text-sm">{feature}</span>
                    </div>
                  ))}
                </div>

                {isCurrentPlan ? (
                  <Button className="w-full" variant="outline" disabled>
                    Current Plan
                  </Button>
                ) : (
                  <Button
                    className={`w-full ${
                      plan.tier === 'pro'
                        ? 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600'
                        : ''
                    }`}
                    onClick={() => handleUpgrade(plan.tier)}
                    variant={plan.tier === 'free' ? 'outline' : 'default'}
                  >
                    {plan.tier === 'free'
                      ? 'Downgrade'
                      : `Upgrade to ${plan.name}`}
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* FAQ Section */}
      <Card className="mt-12">
        <CardHeader>
          <CardTitle>Frequently Asked Questions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="font-medium mb-1">Can I change plans anytime?</div>
            <div className="text-sm text-muted-foreground">
              Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately.
            </div>
          </div>
          <div>
            <div className="font-medium mb-1">What happens to my progress if I downgrade?</div>
            <div className="text-sm text-muted-foreground">
              Your progress, badges, and achievements are never lost. However, some features like the leaderboard may become unavailable.
            </div>
          </div>
          <div>
            <div className="font-medium mb-1">Is there a discount for annual subscriptions?</div>
            <div className="text-sm text-muted-foreground">
              Annual subscriptions offer a 20% discount compared to monthly billing (coming soon).
            </div>
          </div>
          <div>
            <div className="font-medium mb-1">What payment methods do you accept?</div>
            <div className="text-sm text-muted-foreground">
              We accept all major credit cards, PayPal, and bank transfers (integration pending).
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="text-center text-sm text-muted-foreground">
        <p>
          All prices in USD. Cancel anytime. No hidden fees.
          <br />
          This is a demo - no actual payment processing is implemented.
        </p>
      </div>
    </div>
  );
}
