Celery Distributed Features
===========================

This repository is a course project built on top of Celery. It does not use
the original Celery README because the purpose of this workspace is different:
to demonstrate distributed-system concepts through a small, runnable Celery
example.

The project focuses on two features that are being developed and demonstrated:

1. Distributed task tracing with logical clocks.
2. Singleton task execution with Redis-backed distributed mutual exclusion.

Project Goal
============

Celery already provides workers, task queues, brokers, retries, and result
backends. This project uses those building blocks to show how distributed
applications can coordinate work across multiple worker processes.

The implementation is intentionally demo-focused. It keeps the new code inside
``examples/distributed_features`` so the features are easy to inspect, test,
and present without changing Celery's core scheduling protocol.

Feature 1: Distributed Task Tracing With Logical Clocks
======================================================

This feature records a timeline for a related group of tasks. Each task event
belongs to a shared ``trace_id`` and receives a logical clock value so the event
order can be explained without relying only on physical timestamps.

The tracing demo records lifecycle events such as:

- ``started``
- ``sent``
- ``success``
- ``failed``

The trace context includes:

- ``trace_id``: identifier shared by all tasks in the workflow.
- ``task_id``: logical name of the current task.
- ``parent_task_id``: task that caused the current task to run.
- ``worker_id``: worker or process that recorded the event.
- ``logical_clock``: monotonically increasing clock value.
- ``timestamp``: physical time used as a secondary sort key.

This feature connects directly to distributed-system topics such as event
ordering, causality, process communication, and observability.

Feature 2: Singleton Task Execution With Distributed Locks
=========================================================

This feature prevents two workers from executing the same protected task for
the same resource at the same time.

The demo uses Redis as a distributed lock backend. A worker acquires a lock
with ``SET key value NX EX ttl`` semantics before entering the critical section.
The lock stores an owner token, and release only succeeds when the current
worker still owns that token.

The singleton task demo is useful for cases such as:

- updating inventory for one product;
- processing one account balance update;
- running one resource-specific job at a time;
- preventing duplicate work across multiple Celery workers.

The lock also has a TTL so a crashed worker does not block the resource forever.
This feature demonstrates mutual exclusion, coordination, fault tolerance, and
resource ownership in a distributed system.

Repository Layout
=================

The project-specific code is located here:

``examples/distributed_features/app.py``
    Celery app configuration for the demo.

``examples/distributed_features/tasks.py``
    Demo tasks for basic execution, tracing, and singleton locking.

``examples/distributed_features/tracing.py``
    Trace context, trace event model, logical clock helpers, and recorders.

``examples/distributed_features/singleton.py``
    Redis distributed lock helper and singleton task wrapper.

``examples/distributed_features/show_trace.py``
    Command-line script for printing a trace timeline.

``examples/distributed_features/README.md``
    Detailed commands for running the demos.

``Documents_Phenikaa/``
    Course materials, report drafts, and presentation assets.

Requirements
============

- Python with the project dependencies installed.
- Redis running locally on port ``6379``.
- One or more Celery workers for the multi-worker demos.

Run Redis
=========

.. code-block:: bash

    redis-server

Start A Celery Worker
=====================

From the repository root:

.. code-block:: bash

    celery -A examples.distributed_features.app worker -l INFO

For the singleton lock demo, start two workers in separate terminals:

.. code-block:: bash

    celery -A examples.distributed_features.app worker -l INFO -n worker1@%h
    celery -A examples.distributed_features.app worker -l INFO -n worker2@%h

Run The Basic Demo
==================

.. code-block:: bash

    python -m examples.distributed_features.tasks

Run The Tracing Demo
====================

.. code-block:: bash

    python -m examples.distributed_features.tasks run-trace-demo

You can print a stored timeline directly:

.. code-block:: bash

    python examples/distributed_features/show_trace.py order-1-trace

Expected output shape:

.. code-block:: text

    trace_id: order-1-trace
    [1] started process-order on worker-process
    [2] sent process-order on worker-process
    [4] started validate-order on worker-validate parent=process-order
    [5] success validate-order on worker-validate parent=process-order
    [6] success process-order on worker-process

Run The Singleton Lock Demo
===========================

Start two workers first, then run:

.. code-block:: bash

    python -m examples.distributed_features.tasks run-lock-demo

Expected output shape:

.. code-block:: text

    Dispatching two update_inventory tasks for sku-1
    First task id: UUID
    Second task id: UUID
    First result: {'status': 'updated', 'product_id': 'sku-1', 'quantity': 5}
    Second result: {'status': 'skipped', 'reason': 'lock_not_acquired', 'lock_key': 'inventory:sku-1'}

Testing
========

The project includes focused tests for the new demo features:

.. code-block:: bash

    pytest t/unit/examples/test_distributed_tracing.py t/unit/examples/test_singleton_lock.py

Current Scope
=============

This project is not a production monitoring platform and does not replace
Celery's broker protocol. It is an educational extension that uses Celery,
Redis, and Python tests to demonstrate two concrete distributed-system
features.
