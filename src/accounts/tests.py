from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import UserProfile
from accounts.services import CurrentUserService, CurrentUserProfileService
from accounts.grpc import accounts_pb2
from accounts.grpc.accounts_pb2_grpc import (
    CurrentUserControllerStub,
    CurrentUserProfileControllerStub,
    add_CurrentUserControllerServicer_to_server,
    add_CurrentUserProfileControllerServicer_to_server,
)
from grpc_test_utils.fake_grpc import FakeFullAIOGRPC
from asgiref.sync import async_to_sync
from google.protobuf.empty_pb2 import Empty


class TestCurrentUserService(TestCase):
    """Tests for CurrentUserService gRPC methods"""

    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        # Set up fake gRPC
        self.fake_grpc = FakeFullAIOGRPC(
            add_CurrentUserControllerServicer_to_server,
            CurrentUserService.as_servicer(),
        )

    def tearDown(self):
        self.fake_grpc.close()

    def test_get_current_user(self):
        """Test GetCurrentUser returns user information"""
        async def run_test():
            stub = self.fake_grpc.get_fake_stub(CurrentUserControllerStub)
            
            # Call GetCurrentUser
            response = await stub.GetCurrentUser(Empty())
            
            # Verify response
            self.assertEqual(response.id, self.user.id)
            self.assertEqual(response.username, 'testuser')
            self.assertEqual(response.email, 'test@example.com')
            self.assertEqual(response.first_name, 'Test')
            self.assertEqual(response.last_name, 'User')

        async_to_sync(run_test)()

    def test_update_current_user_all_fields(self):
        """Test UpdateCurrentUser updates all fields"""
        async def run_test():
            stub = self.fake_grpc.get_fake_stub(CurrentUserControllerStub)
            
            # Create update request
            request = accounts_pb2.CurrentUserUpdateCurrentUserRequest(
                email='newemail@example.com',
                first_name='NewFirst',
                last_name='NewLast'
            )
            
            # Call UpdateCurrentUser
            response = await stub.UpdateCurrentUser(request)
            
            # Verify response
            self.assertEqual(response.email, 'newemail@example.com')
            self.assertEqual(response.first_name, 'NewFirst')
            self.assertEqual(response.last_name, 'NewLast')
            
            # Verify database was updated
            user = await User.objects.aget(id=self.user.id)
            self.assertEqual(user.email, 'newemail@example.com')
            self.assertEqual(user.first_name, 'NewFirst')
            self.assertEqual(user.last_name, 'NewLast')

        async_to_sync(run_test)()

    def test_update_current_user_partial(self):
        """Test UpdateCurrentUser with partial fields"""
        async def run_test():
            stub = self.fake_grpc.get_fake_stub(CurrentUserControllerStub)
            
            # Create update request with only email
            request = accounts_pb2.CurrentUserUpdateCurrentUserRequest(
                email='partial@example.com'
            )
            
            # Call UpdateCurrentUser
            response = await stub.UpdateCurrentUser(request)
            
            # Verify only email was updated
            self.assertEqual(response.email, 'partial@example.com')
            self.assertEqual(response.first_name, 'Test')  # Unchanged
            self.assertEqual(response.last_name, 'User')  # Unchanged
            
            # Verify database
            user = await User.objects.aget(id=self.user.id)
            self.assertEqual(user.email, 'partial@example.com')
            self.assertEqual(user.first_name, 'Test')
            self.assertEqual(user.last_name, 'User')

        async_to_sync(run_test)()


class TestCurrentUserProfileService(TestCase):
    """Tests for CurrentUserProfileService gRPC methods"""

    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            first_name='Profile',
            last_name='Test'
        )
        
        # Create user profile
        self.profile = UserProfile.objects.create(
            user=self.user,
            bio='Original bio',
            avatar_url='https://example.com/avatar.jpg'
        )
        
        # Set up fake gRPC
        self.fake_grpc = FakeFullAIOGRPC(
            add_CurrentUserProfileControllerServicer_to_server,
            CurrentUserProfileService.as_servicer(),
        )

    def tearDown(self):
        self.fake_grpc.close()

    def test_get_current_user_profile(self):
        """Test GetCurrentUserProfile returns profile with nested user"""
        async def run_test():
            stub = self.fake_grpc.get_fake_stub(CurrentUserProfileControllerStub)
            
            # Call GetCurrentUserProfile
            response = await stub.GetCurrentUserProfile(Empty())
            
            # Verify profile fields
            self.assertEqual(response.id, self.profile.id)
            self.assertEqual(response.bio, 'Original bio')
            self.assertEqual(response.avatar_url, 'https://example.com/avatar.jpg')
            self.assertTrue(response.is_active)
            
            # Verify nested user fields
            self.assertEqual(response.user.id, self.user.id)
            self.assertEqual(response.user.username, 'profileuser')
            self.assertEqual(response.user.email, 'profile@example.com')

        async_to_sync(run_test)()

    def test_get_current_user_profile_creates_if_missing(self):
        """Test GetCurrentUserProfile creates profile if it doesn't exist"""
        async def run_test():
            # Delete existing profile
            await UserProfile.objects.filter(user=self.user).adelete()
            
            stub = self.fake_grpc.get_fake_stub(CurrentUserProfileControllerStub)
            
            # Call GetCurrentUserProfile
            response = await stub.GetCurrentUserProfile(Empty())
            
            # Verify profile was created
            self.assertIsNotNone(response.id)
            self.assertEqual(response.bio, '')  # Default empty
            self.assertEqual(response.user.username, 'profileuser')
            
            # Verify in database
            profile_exists = await UserProfile.objects.filter(user=self.user).aexists()
            self.assertTrue(profile_exists)

        async_to_sync(run_test)()

    def test_update_current_user_profile_all_fields(self):
        """Test UpdateCurrentUserProfile updates all fields"""
        async def run_test():
            stub = self.fake_grpc.get_fake_stub(CurrentUserProfileControllerStub)
            
            # Create update request
            request = accounts_pb2.CurrentUserProfileUpdateCurrentUserProfileRequest(
                bio='Updated bio text',
                avatar_url='https://example.com/new-avatar.jpg'
            )
            
            # Call UpdateCurrentUserProfile
            response = await stub.UpdateCurrentUserProfile(request)
            
            # Verify response
            self.assertEqual(response.bio, 'Updated bio text')
            self.assertEqual(response.avatar_url, 'https://example.com/new-avatar.jpg')
            
            # Verify database was updated
            profile = await UserProfile.objects.aget(id=self.profile.id)
            self.assertEqual(profile.bio, 'Updated bio text')
            self.assertEqual(profile.avatar_url, 'https://example.com/new-avatar.jpg')

        async_to_sync(run_test)()

    def test_update_current_user_profile_partial(self):
        """Test UpdateCurrentUserProfile with partial fields"""
        async def run_test():
            stub = self.fake_grpc.get_fake_stub(CurrentUserProfileControllerStub)
            
            # Create update request with only bio
            request = accounts_pb2.CurrentUserProfileUpdateCurrentUserProfileRequest(
                bio='Only bio updated'
            )
            
            # Call UpdateCurrentUserProfile
            response = await stub.UpdateCurrentUserProfile(request)
            
            # Verify only bio was updated
            self.assertEqual(response.bio, 'Only bio updated')
            self.assertEqual(response.avatar_url, 'https://example.com/avatar.jpg')  # Unchanged
            
            # Verify database
            profile = await UserProfile.objects.aget(id=self.profile.id)
            self.assertEqual(profile.bio, 'Only bio updated')
            self.assertEqual(profile.avatar_url, 'https://example.com/avatar.jpg')

        async_to_sync(run_test)()

    def test_update_current_user_profile_creates_if_missing(self):
        """Test UpdateCurrentUserProfile creates profile if it doesn't exist"""
        async def run_test():
            # Delete existing profile
            await UserProfile.objects.filter(user=self.user).adelete()
            
            stub = self.fake_grpc.get_fake_stub(CurrentUserProfileControllerStub)
            
            # Create update request
            request = accounts_pb2.CurrentUserProfileUpdateCurrentUserProfileRequest(
                bio='New profile bio',
                avatar_url='https://example.com/created-avatar.jpg'
            )
            
            # Call UpdateCurrentUserProfile
            response = await stub.UpdateCurrentUserProfile(request)
            
            # Verify profile was created with values
            self.assertIsNotNone(response.id)
            self.assertEqual(response.bio, 'New profile bio')
            self.assertEqual(response.avatar_url, 'https://example.com/created-avatar.jpg')
            
            # Verify in database
            profile = await UserProfile.objects.aget(user=self.user)
            self.assertEqual(profile.bio, 'New profile bio')
            self.assertEqual(profile.avatar_url, 'https://example.com/created-avatar.jpg')

        async_to_sync(run_test)()


class TestUserProfileIntegration(TestCase):
    """Integration tests for User and UserProfile services together"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com'
        )
        
        self.user_fake_grpc = FakeFullAIOGRPC(
            add_CurrentUserControllerServicer_to_server,
            CurrentUserService.as_servicer(),
        )
        
        self.profile_fake_grpc = FakeFullAIOGRPC(
            add_CurrentUserProfileControllerServicer_to_server,
            CurrentUserProfileService.as_servicer(),
        )

    def tearDown(self):
        self.user_fake_grpc.close()
        self.profile_fake_grpc.close()

    def test_update_user_and_profile(self):
        """Test updating both user info and profile"""
        async def run_test():
            user_stub = self.user_fake_grpc.get_fake_stub(CurrentUserControllerStub)
            profile_stub = self.profile_fake_grpc.get_fake_stub(CurrentUserProfileControllerStub)
            
            # Update user
            user_request = accounts_pb2.CurrentUserUpdateCurrentUserRequest(
                email='updated@example.com',
                first_name='Updated',
                last_name='Name'
            )
            user_response = await user_stub.UpdateCurrentUser(user_request)
            
            # Update profile
            profile_request = accounts_pb2.CurrentUserProfileUpdateCurrentUserProfileRequest(
                bio='Integration test bio',
                avatar_url='https://example.com/integration.jpg'
            )
            profile_response = await profile_stub.UpdateCurrentUserProfile(profile_request)
            
            # Verify user updates
            self.assertEqual(user_response.email, 'updated@example.com')
            self.assertEqual(user_response.first_name, 'Updated')
            
            # Verify profile updates and nested user
            self.assertEqual(profile_response.bio, 'Integration test bio')
            self.assertEqual(profile_response.user.email, 'updated@example.com')
            self.assertEqual(profile_response.user.first_name, 'Updated')

        async_to_sync(run_test)()
