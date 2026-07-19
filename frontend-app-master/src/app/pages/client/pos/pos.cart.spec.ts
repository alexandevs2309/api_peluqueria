import { TestBed } from '@angular/core/testing'
import { PosCart } from './pos.cart'
import { LocaleService } from '../../../core/services/locale/locale.service'

describe('PosCart', () => {
  let cart: PosCart
  let localeServiceMock: any

  beforeEach(() => {
    localeServiceMock = {
      t: jasmine.createSpy('t').and.callFake((key: string) => {
        if (key === 'pos.validation.select_employee') return 'Debe seleccionar un empleado'
        return key
      })
    }

    TestBed.configureTestingModule({
      providers: [
        PosCart,
        { provide: LocaleService, useValue: localeServiceMock }
      ]
    })

    cart = TestBed.inject(PosCart)
    cart.isOpen.set(true)
    localStorage.clear()
  })


  it('starts empty', () => {
    expect(cart.items().length).toBe(0)
    expect(cart.total()).toBe(0)
    expect(cart.canSell()).toBeFalse()
  })

  it('adds an item', () => {
    const item = { id: 1, name: 'Corte', price: '500', stock: 10 }
    const result = cart.addItem(item, 'service')
    expect(result).toBeTrue()
    expect(cart.items().length).toBe(1)
    expect(cart.items()[0].quantity).toBe(1)
    expect(cart.items()[0].subtotal).toBe(500)
  })

  it('increments quantity on duplicate add', () => {
    const item = { id: 1, name: 'Corte', price: '500' }
    cart.addItem(item, 'service')
    cart.addItem(item, 'service')
    expect(cart.items().length).toBe(1)
    expect(cart.items()[0].quantity).toBe(2)
    expect(cart.items()[0].subtotal).toBe(1000)
  })

  it('rejects adding out-of-stock product', () => {
    const item = { id: 1, name: 'Producto', price: '100', stock: 0 }
    const result = cart.addItem(item, 'product')
    expect(result).toBeFalse()
    expect(cart.items().length).toBe(0)
  })

  it('computes subtotal, discount, and total', () => {
    cart.addItem({ id: 1, name: 'Corte', price: '1000' }, 'service')
    cart.addItem({ id: 2, name: 'Barba', price: '500' }, 'service')
    expect(cart.subtotal()).toBe(1500)

    cart.discount.set(200)
    expect(cart.discountValue()).toBe(200)
    expect(cart.total()).toBe(1300)
  })

  it('computes percentage discount', () => {
    cart.addItem({ id: 1, name: 'Corte', price: '1000' }, 'service')
    cart.discount.set(10)
    cart.discountType.set('%')
    expect(cart.discountValue()).toBe(100)
    expect(cart.total()).toBe(900)
  })

  it('updates item quantity', () => {
    cart.addItem({ id: 1, name: 'Corte', price: '500' }, 'service')
    cart.updateQuantity(0, 2)
    expect(cart.items()[0].quantity).toBe(3)
    expect(cart.items()[0].subtotal).toBe(1500)
  })

  it('removes item when quantity reaches 0', () => {
    cart.addItem({ id: 1, name: 'Corte', price: '500' }, 'service')
    cart.updateQuantity(0, -1)
    expect(cart.items().length).toBe(0)
  })

  it('removes item by index', () => {
    cart.addItem({ id: 1, name: 'Corte', price: '500' }, 'service')
    cart.removeItem(0)
    expect(cart.items().length).toBe(0)
  })

  it('clears entire cart', () => {
    cart.addItem({ id: 1, name: 'Corte', price: '500' }, 'service')
    cart.client.set({ id: 1 })
    cart.paymentMethod.set('cash')
    cart.discount.set(50)
    cart.clear()
    expect(cart.items().length).toBe(0)
    expect(cart.client()).toBeNull()
    expect(cart.paymentMethod()).toBe('')
    expect(cart.discount()).toBe(0)
  })

  it('computes change', () => {
    cart.addItem({ id: 1, name: 'Corte', price: '500' }, 'service')
    cart.receivedAmount.set(1000)
    expect(cart.change()).toBe(500)
  })

  it('sets canSell correctly', () => {
    expect(cart.canSell()).toBeFalse()
    cart.addItem({ id: 1, name: 'Corte', price: '500' }, 'service')
    cart.paymentMethod.set('cash')
    cart.employee.set({ id: 1 })
    expect(cart.canSell()).toBeTrue()
  })

  it('requires employee for services', () => {
    cart.addItem({ id: 1, name: 'Corte', price: '500' }, 'service')
    cart.paymentMethod.set('cash')
    expect(cart.canSell()).toBeFalse()
    expect(cart.validationMessage()).toContain('empleado')
    cart.employee.set({ id: 1 })
    expect(cart.canSell()).toBeTrue()
  })

  it('handles mixed payments', () => {
    cart.addItem({ id: 1, name: 'Corte', price: '1000' }, 'service')
    expect(cart.addMixedPayment('cash', 500)).toBeTrue()
    expect(cart.addMixedPayment('card', 600)).toBeTrue()
    expect(cart.mixedTotal()).toBe(1100)
    expect(cart.mixedValid()).toBeTrue()
  })

  it('rejects invalid mixed payment', () => {
    expect(cart.addMixedPayment('', 0)).toBeFalse()
    expect(cart.mixedPayments().length).toBe(0)
  })

  it('tracks stock in cart', () => {
    const item = { id: 1, name: 'Shampoo', price: '200', stock: 5 }
    cart.addItem(item, 'product')
    cart.addItem(item, 'product')
    expect(cart.stockInCart(1)).toBe(2)
    expect(cart.availableStock(item)).toBe(3)
    expect(cart.canAddMore(item)).toBeTrue()
  })

  it('records daily stats', () => {
    cart.recordSale(1500, 'cash')
    expect(cart.dailyStats().ventas).toBe(1)
    expect(cart.dailyStats().ingresos).toBe(1500)
    expect(cart.cashSales()).toBe(1500)
    cart.recordSale(500, 'card')
    expect(cart.dailyStats().ventas).toBe(2)
    expect(cart.dailyStats().ingresos).toBe(2000)
  })

  it('resets daily stats', () => {
    cart.recordSale(500, 'cash')
    cart.resetDailyStats()
    expect(cart.dailyStats().ventas).toBe(0)
    expect(cart.dailyStats().ingresos).toBe(0)
  })

  it('computes expected cash and count difference', () => {
    cart.cashStartAmount.set(1000)
    cart.recordSale(500, 'cash')
    expect(cart.expectedCash()).toBe(1500)
    cart.denominations.set(
      [2000, 1000].map(v => ({ valor: v, cantidad: 1, total: v }))
    )
    expect(cart.countTotal()).toBe(3000)
    expect(cart.countDifference()).toBe(1500)
  })

  it('toggles discount type', () => {
    expect(cart.discountType()).toBe('$')
    cart.toggleDiscountType()
    expect(cart.discountType()).toBe('%')
    cart.toggleDiscountType()
    expect(cart.discountType()).toBe('$')
  })

  it('applies promotion', () => {
    const promo = { discount_value: 15, type: '%' }
    cart.applyPromotion(promo)
    expect(cart.promoApplied()).toEqual(promo)
    expect(cart.discount()).toBe(15)
  })
})
