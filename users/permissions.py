from rest_framework import permissions


class IsManagerOrHR(permissions.BasePermission):
    """
    Custom permission to allow only managers and HR users.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Allow managers and HR users
        return request.user.role in ['manager', 'hr']


class IsEmployeeOrManagerOrHR(permissions.BasePermission):
    """
    Custom permission to allow employees, managers, and HR users.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Allow all authenticated users (employees, managers, HR)
        return True
    
    def has_object_permission(self, request, view, obj):
        # Employees can only access their own objects
        if request.user.role == 'employee':
            # Check if the object belongs to the user
            if hasattr(obj, 'employee'):
                return obj.employee == request.user
            elif hasattr(obj, 'user'):
                return obj.user == request.user
            elif hasattr(obj, 'created_by'):
                return obj.created_by == request.user
        
        # Managers and HR can access all objects
        return request.user.role in ['manager', 'hr']


class IsOwnerOrManagerOrHR(permissions.BasePermission):
    """
    Custom permission to allow object owners, managers, and HR users.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Allow all authenticated users
        return True
    
    def has_object_permission(self, request, view, obj):
        # Managers and HR can access all objects
        if request.user.role in ['manager', 'hr']:
            return True
        
        # Employees can only access their own objects
        if request.user.role == 'employee':
            # Check if the object belongs to the user
            if hasattr(obj, 'employee'):
                return obj.employee == request.user
            elif hasattr(obj, 'user'):
                return obj.user == request.user
            elif hasattr(obj, 'created_by'):
                return obj.created_by == request.user
        
        return False


class IsManagerOrHROrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read access to all authenticated users,
    but write access only to managers and HR users.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Allow read access to all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Allow write access only to managers and HR users
        return request.user.role in ['manager', 'hr']


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read access to all authenticated users,
    but write access only to object owners, managers, and HR users.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Allow read access to all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Allow write access to all authenticated users
        return True
    
    def has_object_permission(self, request, view, obj):
        # Allow read access to all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Managers and HR can modify all objects
        if request.user.role in ['manager', 'hr']:
            return True
        
        # Employees can only modify their own objects
        if request.user.role == 'employee':
            # Check if the object belongs to the user
            if hasattr(obj, 'employee'):
                return obj.employee == request.user
            elif hasattr(obj, 'user'):
                return obj.user == request.user
            elif hasattr(obj, 'created_by'):
                return obj.created_by == request.user
        
        return False
