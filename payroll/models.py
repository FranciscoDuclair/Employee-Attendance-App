from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class Payroll(models.Model):
    """
    Model to track employee payroll information
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payroll_records')
    month = models.IntegerField(help_text="Month (1-12)")
    year = models.IntegerField(help_text="Year")
    
    # Basic salary information
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    # Attendance calculations
    total_hours_worked = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    regular_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    
    # Pay calculations
    regular_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    overtime_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Deductions
    tax_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Net pay
    gross_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    net_pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Status and approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_payrolls'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payroll'
        unique_together = ['user', 'month', 'year']
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.month}/{self.year}"
    
    def calculate_gross_pay(self):
        """Calculate gross pay based on hours and rates"""
        self.gross_pay = self.regular_pay + self.overtime_pay
        return self.gross_pay
    
    def calculate_net_pay(self):
        """Calculate net pay after deductions"""
        self.net_pay = self.gross_pay - self.tax_deduction - self.other_deductions
        return self.net_pay
