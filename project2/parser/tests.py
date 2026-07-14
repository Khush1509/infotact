from django.test import TestCase
from django.urls import reverse

class HealthCheckTests(TestCase):
    def test_health_check_endpoint(self):
        """
        Verify that the health check endpoint returns 200 and indicates active status.
        """
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['database'], 'connected')
        self.assertIsNone(data['error'])

