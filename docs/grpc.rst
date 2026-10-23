GRPC in SpienX Hub
=======================

Work Flow for Creating a gRPC Service
-------------------------------------

This guide outlines the steps to add a new gRPC service to the Spienx Hub, using `django-socio-grpc`.

1. Define the Serializer
^^^^^^^^^^^^^^^^^^^^^^^^

Create or update the `serializers.py` in your app. The serializer should inherit from `django_socio_grpc.proto_serializers.ModelProtoSerializer`.

At this stage, you might not have the proto classes generated yet, so you can omit `proto_class` and `proto_class_list` temporarily or define the fields first.

.. code-block:: python

    from django_socio_grpc import proto_serializers
    from .models import MyModel

    class MyModelProtoSerializer(proto_serializers.ModelProtoSerializer):
        class Meta:
            model = MyModel
            fields = ['id', 'name', 'created_at']

2. Define the Service
^^^^^^^^^^^^^^^^^^^^^

Create or update `services.py` in your app. The service should inherit from one of the generics provided by `django_socio_grpc`. Prefer **Async** generics (e.g., `AsyncReadOnlyModelService`) for better performance and compatibility with the async gRPC server.

.. code-block:: python

    from django_socio_grpc import generics
    from .models import MyModel
    from .serializers import MyModelProtoSerializer

    class MyModelService(generics.AsyncReadOnlyModelService):
        queryset = MyModel.objects.all()
        serializer_class = MyModelProtoSerializer

3. Define Custom Actions (Optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you need custom RPC methods beyond standard CRUD operations (like streaming or specific business logic), use the ``@grpc_action`` decorator.

.. code-block:: python

    from django_socio_grpc.decorators import grpc_action
    from .serializers import PageProtoSerializer

    class MyModelService(generics.AsyncReadOnlyModelService):
        # ...

        @grpc_action(
            request=[{"name": "some_id", "type": "int64"}],
            response=PageProtoSerializer,
            response_stream=True,  # Set to True for streaming responses
        )
        async def StreamThings(self, request, context):
            some_id = request.some_id
            
            # Use aget for async retrieval
            instance = await MyModel.objects.prefetch_related('related_items').aget(pk=some_id)
            
            for item in instance.related_items.all():
                serializer = PageProtoSerializer(item)
                yield serializer.message

4. Register the Service
^^^^^^^^^^^^^^^^^^^^^^^

Register your new service in `src/config/grpc_handlers.py` to expose it.

.. code-block:: python

    from myapp.services import MyModelService

    def grpc_handlers(server):
        # ... other registrations ...
        
        app_registry = AppHandlerRegistry('myapp', server)
        app_registry.register(MyModelService, service_file_path='myapp.grpc')

5. Generate Proto Files
^^^^^^^^^^^^^^^^^^^^^^^

Run the management command to generate the `.proto` definitions and the corresponding Python gRPC code (`_pb2.py` and `_pb2_grpc.py`).

.. code-block:: bash

    cd src
    poetry run python manage.py generateproto

Definitions are stored in the ``spienx-proto`` Git submodule at
``spienx-proto/<app>/grpc/<app>.proto``. Initialize it from the repository
root before generation or Docker builds:

.. code-block:: bash

    git submodule update --init --recursive

The ``src/<app>/grpc/<app>.proto`` paths are relative symlinks to the shared
definitions. The normal generation command writes through these symlinks and
keeps Python stubs in ``src/<app>/grpc/``, preserving existing imports and
protobuf field numbering. Do not replace the symlinks with copies.

For a new app, prepare its shared definition and symlink from the repository
root before running generation:

.. code-block:: bash

    mkdir -p spienx-proto/myapp/grpc src/myapp/grpc
    touch spienx-proto/myapp/grpc/myapp.proto
    ln -s ../../../spienx-proto/myapp/grpc/myapp.proto src/myapp/grpc/myapp.proto

Commit and push definition changes in the submodule first, then commit its
updated pointer alongside service changes and generated Python stubs in
``spienx-hub``. Review both repositories before committing:

.. code-block:: bash

    git -C spienx-proto diff
    git diff --submodule

6. Link Serializer to Proto Classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now that the proto files are generated, update your serializer to explicitly link to the generated message classes. This is often required for the serializer to correctly instantiation return messages, especially in async contexts.

.. code-block:: python

    from myapp.grpc import myapp_pb2  # Import generated pb2

    class MyModelProtoSerializer(proto_serializers.ModelProtoSerializer):
        class Meta:
            model = MyModel
            # Link to generated messages
            proto_class = myapp_pb2.MyModelResponse
            proto_class_list = myapp_pb2.MyModelListResponse
            fields = ['id', 'name', 'created_at']

7. Test the Service
^^^^^^^^^^^^^^^^^^^

Create tests using `FakeFullAIOGRPC` to verify your service without spinning up a full server.

.. code-block:: python

    from django.test import TestCase
    from grpc_test_utils.fake_grpc import FakeFullAIOGRPC
    from myapp.services import MyModelService
    from myapp.grpc.myapp_pb2_grpc import MyModelControllerStub, add_MyModelControllerServicer_to_server
    from asgiref.sync import async_to_sync

    class TestMyModelService(TestCase):
        def setUp(self):
            # ... setup data ...
            self.fake_grpc = FakeFullAIOGRPC(
                add_MyModelControllerServicer_to_server,
                MyModelService.as_servicer(),
            )

        def tearDown(self):
            self.fake_grpc.close()

        def test_list(self):
            async def run_test():
                stub = self.fake_grpc.get_fake_stub(MyModelControllerStub)
                response = await stub.List(myapp_pb2.MyModelListRequest())
                self.assertTrue(len(response.results) > 0)
            
            async_to_sync(run_test)()

Diagnosing repository list permissions
--------------------------------------

``GitRepositoryController.List`` logs its permission decision in
``repositories.services``: the controller, action, permission class,
``is_authenticated``, ``is_superuser``, and ``allowed``. Denials are logged
at WARNING and successful checks at INFO; no cookies or credentials are logged.

After restarting the web service, reproduce the frontend request and inspect:

.. code-block:: bash

    docker compose logs --since=2m web

An unauthenticated result means the gRPC request did not resolve to a logged-in
user, even if the browser has an authenticated Django admin session. An
authenticated non-superuser can also be denied by the current policy: it checks
lowercase ``list``/``retrieve`` while RPC actions are named ``List``/``Retrieve``.
Authenticated superusers bypass that action check.

``core.authentication`` also logs why session authentication failed, without
logging cookie values: ``missing_cookie_header``, ``missing_session_cookie``,
``session_not_found``, ``missing_session_user``, ``user_not_found``, or
``inactive_user``. These distinguish a browser credential-forwarding problem
from a session lookup problem.
