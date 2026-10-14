import { Popover as PopoverPrimitive } from 'radix-ui'
import { forwardRef, type ComponentPropsWithoutRef, type ElementRef } from 'react'

export const Popover = PopoverPrimitive.Root
export const PopoverTrigger = PopoverPrimitive.Trigger
export const PopoverClose = PopoverPrimitive.Close

type PopoverContentProps = ComponentPropsWithoutRef<typeof PopoverPrimitive.Content> & {
  container?: HTMLElement | null
}

export const PopoverContent = forwardRef<ElementRef<typeof PopoverPrimitive.Content>, PopoverContentProps>(
  ({ align = 'center', collisionPadding = 8, container, sideOffset = 4, ...props }, ref) => (
    <PopoverPrimitive.Portal container={container}>
      <PopoverPrimitive.Content align={align} collisionPadding={collisionPadding} ref={ref} sideOffset={sideOffset} {...props} />
    </PopoverPrimitive.Portal>
  ),
)
PopoverContent.displayName = 'PopoverContent'
