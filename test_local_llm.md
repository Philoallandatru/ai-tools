# NVMe Controller Initialization Test

## Controller Initialization Sequence

The NVMe controller initialization must follow these steps:

1. **Set CC.EN to 1**: Enable the controller by setting the Controller Configuration Enable bit
2. **Wait for CSTS.RDY**: Poll the Controller Status Ready bit until it becomes 1
3. **Configure Admin Queue**: Set up the Admin Submission and Completion Queues
4. **Create I/O Queues**: Initialize I/O Submission and Completion Queue pairs

### Timing Requirements

- The controller must set CSTS.RDY within CAP.TO seconds after CC.EN is set
- Typical timeout value: 500ms to 2 seconds
- If timeout occurs, the initialization fails and controller reset is required

### Error Handling

If CSTS.RDY does not become 1 within the timeout period:
1. Log the timeout error
2. Clear CC.EN to 0
3. Wait for CSTS.RDY to become 0
4. Retry initialization or report fatal error
