from django import forms
from .models import BorrowRequest, facultyItem
from .models import EmailNotification

class BorrowRequestMultimediaForm(forms.ModelForm):
    item = forms.ModelChoiceField(queryset=None, label='Item')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # Filter items based on the logged-in user
            self.fields['item'].queryset = facultyItem.objects.filter(user=user)
        else:
            self.fields['item'].queryset = facultyItem.objects.none()

        # Add class form-control to item field
        self.fields['item'].widget.attrs.update({'class': 'form-control'})

        # Customize the display of the dropdown items
        self.fields['item'].label_from_instance = lambda obj: f"{obj.name} (Available stock: {obj.quantity})"

    class Meta:
        model = BorrowRequest
        fields = [
            'student_id', 'name', 'course', 'year', 'email', 'phone', 
            'date_borrow', 'date_return', 'item', 'purpose', 'status', 'note'
        ]
        widgets = {
            'student_id': forms.TextInput(attrs={'class': 'form-control', 'style': 'border: 1px solid #bebebe;', 'placeholder': 'Enter Student ID'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'style': 'border: 1px solid #bebebe;', 'placeholder': 'Enter Full Name'}),
            'course': forms.TextInput(attrs={'class': 'form-control', 'style': 'border: 1px solid #bebebe;', 'placeholder': 'Enter Course'}),
            'year': forms.Select(attrs={'class': 'form-control', 'style': 'border: 1px solid #bebebe;'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'style': 'border: 1px solid #bebebe;', 'placeholder': 'Enter your Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'style': 'border: 1px solid #bebebe;', 'placeholder': 'Phone Number'}),
            'date_borrow': forms.DateInput(attrs={
                'class': 'form-control datetimepicker-input datepicker-default', 
                'id': 'datepicker',
                'data-target': '#reservationdate',
                'style': 'border: 1px solid #bebebe;',
                'required': 'required',
                'placeholder': 'Select date'
            }),
            'date_return': forms.DateInput(attrs={'class': 'datepicker-default form-control', 'id': 'datepicker-return', 'style': 'border: 1px solid #bebebe;'}),
            'purpose': forms.Textarea(attrs={'class': 'summernote form-control', 'style': 'border: 1px solid #bebebe;', 'placeholder': 'Type here...'}),
            'status': forms.TextInput(attrs={'class': 'form-control', 'style': 'border: 1px solid #bebebe;', 'readonly': 'readonly'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'style': 'border: 1px solid #bebebe;'}),
        }

class EmailNotificationForm(forms.ModelForm):
    class Meta:
        model = EmailNotification
        fields = ['title', 'message', 'email']
