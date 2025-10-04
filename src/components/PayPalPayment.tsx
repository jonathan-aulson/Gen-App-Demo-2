import React, { useEffect, useRef } from "react";

interface PayPalPaymentProps {
  totalAmount: number;
  onSuccess: () => void;
  onFailure: () => void;
}

const PayPalPayment: React.FC<PayPalPaymentProps> = ({ totalAmount, onSuccess, onFailure }) => {
  const paypalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!window.paypal) return;

    window.paypal
      .Buttons({
        createOrder: (_: any, actions: any) => {
          return actions.order.create({
            purchase_units: [
              {
                amount: {
                  value: totalAmount.toFixed(2)
                }
              }
            ]
          });
        },
        onApprove: async (_: any, actions: any) => {
          try {
            await actions.order.capture();
            onSuccess();
          } catch (error) {
            console.error("PayPal approval error:", error);
            onFailure();
          }
        },
        onError: (err: any) => {
          console.error("PayPal error:", err);
          onFailure();
        }
      })
      .render(paypalRef.current!);
  }, [totalAmount, onSuccess, onFailure]);

  return (
    <div>
      <h3 className="text-lg font-semibold text-navy-700 mb-2">Pay with PayPal</h3>
      <div ref={paypalRef}></div>
    </div>
  );
};

export default PayPalPayment;