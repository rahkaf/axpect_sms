"""
GPS utility functions for geofencing and location calculations
"""
import math
from decimal import Decimal
from django.db import models


def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two GPS coordinates using Haversine formula"""
    # Convert to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [float(lat1), float(lng1), float(lat2), float(lng2)])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth's radius in meters
    r = 6371000
    
    return c * r


def is_in_geofence(latitude, longitude, geofence):
    """Check if coordinates are within a geofence"""
    if not geofence.is_active:
        return False
    
    distance = calculate_distance(
        latitude, longitude,
        geofence.center_latitude, geofence.center_longitude
    )
    
    return distance <= geofence.radius_meters


def find_applicable_geofences(latitude, longitude, employee):
    """Find all geofences that apply to an employee's location"""
    from .models import EmployeeGeofence
    
    geofences = EmployeeGeofence.objects.filter(
        is_active=True
    ).filter(
        models.Q(department=employee.department) | 
        models.Q(department__isnull=True)
    )
    
    applicable = []
    for geofence in geofences:
        if is_in_geofence(latitude, longitude, geofence):
            applicable.append(geofence)
    
    return applicable


def validate_coordinates(latitude, longitude):
    """Validate GPS coordinates are within valid ranges"""
    try:
        lat = float(latitude)
        lng = float(longitude)
        
        if not (-90 <= lat <= 90):
            return False, "Latitude must be between -90 and 90 degrees"
        
        if not (-180 <= lng <= 180):
            return False, "Longitude must be between -180 and 180 degrees"
        
        return True, "Valid coordinates"
        
    except (ValueError, TypeError):
        return False, "Invalid coordinate format"


def calculate_route_distance(route_points):
    """Calculate total distance for a route with multiple GPS points"""
    if len(route_points) < 2:
        return 0
    
    total_distance = 0
    for i in range(1, len(route_points)):
        prev_point = route_points[i-1]
        curr_point = route_points[i]
        
        distance = calculate_distance(
            prev_point['lat'], prev_point['lng'],
            curr_point['lat'], curr_point['lng']
        )
        total_distance += distance
    
    return total_distance


def calculate_speed(point1, point2):
    """Calculate speed between two GPS points with timestamps"""
    from datetime import datetime
    
    # Calculate distance
    distance = calculate_distance(
        point1['lat'], point1['lng'],
        point2['lat'], point2['lng']
    )
    
    # Calculate time difference
    if isinstance(point1['timestamp'], str):
        time1 = datetime.fromisoformat(point1['timestamp'].replace('Z', '+00:00'))
    else:
        time1 = point1['timestamp']
        
    if isinstance(point2['timestamp'], str):
        time2 = datetime.fromisoformat(point2['timestamp'].replace('Z', '+00:00'))
    else:
        time2 = point2['timestamp']
    
    time_diff = abs((time2 - time1).total_seconds())
    
    if time_diff == 0:
        return 0
    
    # Speed in km/h
    speed_ms = distance / time_diff
    speed_kmh = speed_ms * 3.6
    
    return speed_kmh


def get_location_type(latitude, longitude, employee):
    """Determine location type (office, field, remote) based on geofences"""
    from .models import EmployeeGeofence
    
    # Check office geofences first
    office_geofences = EmployeeGeofence.objects.filter(
        fence_type='OFFICE',
        is_active=True
    ).filter(
        models.Q(department=employee.department) | 
        models.Q(department__isnull=True)
    )
    
    for geofence in office_geofences:
        if is_in_geofence(latitude, longitude, geofence):
            return 'office'
    
    # Check work site geofences
    work_geofences = EmployeeGeofence.objects.filter(
        fence_type__in=['WORK_SITE', 'FIELD'],
        is_active=True
    ).filter(
        models.Q(department=employee.department) | 
        models.Q(department__isnull=True)
    )
    
    for geofence in work_geofences:
        if is_in_geofence(latitude, longitude, geofence):
            return 'field'
    
    # Check client geofences
    client_geofences = EmployeeGeofence.objects.filter(
        fence_type='CLIENT',
        is_active=True
    ).filter(
        models.Q(department=employee.department) | 
        models.Q(department__isnull=True)
    )
    
    for geofence in client_geofences:
        if is_in_geofence(latitude, longitude, geofence):
            return 'client'
    
    # Default to remote if not in any geofence
    return 'remote'


def format_coordinates(latitude, longitude, precision=6):
    """Format coordinates to specified decimal places"""
    try:
        lat = round(float(latitude), precision)
        lng = round(float(longitude), precision)
        return lat, lng
    except (ValueError, TypeError):
        return None, None


def get_address_from_coordinates(latitude, longitude):
    """Get address from coordinates (placeholder for geocoding service)"""
    # In production, this would integrate with a geocoding service like Google Maps
    # For now, return a formatted coordinate string
    return f"Location: {latitude:.6f}, {longitude:.6f}"


def calculate_geofence_coverage(geofences, bounds):
    """Calculate what percentage of an area is covered by geofences"""
    # This is a simplified calculation
    # In production, this would use proper geometric calculations
    
    total_area = 0
    for geofence in geofences:
        if geofence.is_active:
            # Approximate area of circle in square meters
            area = math.pi * (geofence.radius_meters ** 2)
            total_area += area
    
    return total_area


def detect_anomalous_movement(gps_tracks, max_speed_kmh=200):
    """Detect potentially anomalous GPS movements"""
    if len(gps_tracks) < 2:
        return []
    
    anomalies = []
    
    for i in range(1, len(gps_tracks)):
        prev_track = gps_tracks[i-1]
        curr_track = gps_tracks[i]
        
        # Calculate speed between points
        point1 = {
            'lat': float(prev_track.latitude),
            'lng': float(prev_track.longitude),
            'timestamp': prev_track.timestamp
        }
        
        point2 = {
            'lat': float(curr_track.latitude),
            'lng': float(curr_track.longitude),
            'timestamp': curr_track.timestamp
        }
        
        speed = calculate_speed(point1, point2)
        
        if speed > max_speed_kmh:
            anomalies.append({
                'track_id': curr_track.id,
                'speed': speed,
                'timestamp': curr_track.timestamp,
                'message': f'Unusually high speed: {speed:.1f} km/h'
            })
    
    return anomalies
