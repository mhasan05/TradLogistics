from django.urls import path
from .views import *

urlpatterns = [
    path("driver/withdraw/", DriverWithdrawRequestAPIView.as_view()),
    path("admin/withdraw/<int:withdraw_id>/process/", AdminProcessWithdrawAPIView.as_view()),

    path("driver/wallet-summary/", DriverWalletSummaryAPIView.as_view()),
    path("driver/earnings-summary/", DriverEarningsSummaryAPIView.as_view()),
    path("driver/earnings-dashboard/", DriverEarningsDashboardAPIView.as_view()),
]