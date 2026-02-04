from .razorpay_client import get_razorpay_client


def create_razorpay_order(amount):
    client = get_razorpay_client()
    return client.order.create({
        "amount": amount * 100,
        "currency": "INR",
        "payment_capture": 1
    })


def fetch_razorpay_payment(payment_id):
    client = get_razorpay_client()
    return client.payment.fetch(payment_id)
