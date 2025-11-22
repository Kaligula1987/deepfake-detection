# app/payments.py
import stripe
stripe.api_key = "your_stripe_secret_key"

def create_checkout_session(user_id: str):
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'eur',
                'product_data': {
                    'name': 'Deepfake Detection Premium',
                },
                'unit_amount': 500,  # €5.00
            },
            'quantity': 1,
        }],
        mode='subscription',
        success_url='https://yourdomain.com/success',
        cancel_url='https://yourdomain.com/cancel',
    )
    return session
