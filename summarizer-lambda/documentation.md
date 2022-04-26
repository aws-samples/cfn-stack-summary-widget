Renders an HTML summary of one or more CloudFormation stacks. To render a
summary of a stack named `MyStack` and another stack named `MyOtherStack`, put 
the following YAML into the `parameters` input of your custom widget.

```yaml
stacks:
  - MyStack
  - MyOtherStack
```