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

3. Register the Service
^^^^^^^^^^^^^^^^^^^^^^^

Register your new service in `src/config/grpc_handlers.py` to expose it.

.. code-block:: python

    from myapp.services import MyModelService

    def grpc_handlers(server):
        # ... other registrations ...
        
        app_registry = AppHandlerRegistry('myapp', server)
        app_registry.register(MyModelService, service_file_path='myapp.grpc')

4. Generate Proto Files
^^^^^^^^^^^^^^^^^^^^^^^

Run the management command to generate the `.proto` definitions and the corresponding Python gRPC code (`_pb2.py` and `_pb2_grpc.py`).

.. code-block:: bash

    cd src
    poetry run python manage.py generateproto

This will create/update the `src/myapp/grpc/` directory.

5. Link Serializer to Proto Classes
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

6. Test the Service
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

