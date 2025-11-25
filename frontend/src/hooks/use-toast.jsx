/* eslint-disable react-refresh/only-export-components */
import * as React from "react"

const TOAST_LIMIT = 1

const actionTypes = {
  ADD_TOAST: "ADD_TOAST",
  UPDATE_TOAST: "UPDATE_TOAST",
  DISMISS_TOAST: "DISMISS_TOAST",
  REMOVE_TOAST: "REMOVE_TOAST",
}

let count = 0

function genId() {
  count = (count + 1) % Number.MAX_SAFE_INTEGER
  return count.toString()
}

const toastTimeouts = new Map()

 

const reducer = (state, action) => {
  switch (action.type) {
    case actionTypes.ADD_TOAST:
      return {
        ...state,
        toasts: [action.toast, ...state.toasts].slice(0, TOAST_LIMIT),
      }

    case actionTypes.UPDATE_TOAST:
      return {
        ...state,
        toasts: state.toasts.map((t) =>
          t.id === action.toast.id ? { ...t, ...action.toast } : t
        ),
      }

    case actionTypes.DISMISS_TOAST: {
      const { toastId } = action

      // ! Side effects ! Clear and disable timeouts
      if (toastId) {
        clearTimeout(toastTimeouts.get(toastId))
        toastTimeouts.delete(toastId)
      }

      return {
        ...state,
        toasts: state.toasts.map((t) =>
          t.id === toastId ? { ...t, open: false } : t
        ),
      }
    }
    case actionTypes.REMOVE_TOAST:
      if (action.toastId === undefined) {
        return { ...state, toasts: [] }
      }
      return {
        ...state,
        toasts: state.toasts.filter((t) => t.id !== action.toastId),
      }
    default:
      throw new Error()
  }
}

const ToastContext = React.createContext(undefined)

const AppToastProvider = ({ children }) => {
  const [state, dispatch] = React.useReducer(reducer, { toasts: [] })

  const getToast = React.useCallback((props) => {
    const id = genId()
    const update = (props) =>
      dispatch({
        type: actionTypes.UPDATE_TOAST,
        toast: { ...props, id },
      })
    const dismiss = () => dispatch({ type: actionTypes.DISMISS_TOAST, toastId: id })

    dispatch({
      type: actionTypes.ADD_TOAST,
      toast: {
        ...props,
        id,
        open: true,
        onOpenChange: (open) => {
          if (!open) {
            dismiss()
          }
        },
      },
    })

    return { id, update, dismiss }
  }, [])

  return (
    <ToastContext.Provider value={{ toasts: state.toasts, toast: getToast }}>
      {children}
    </ToastContext.Provider>
  )
}

function useToast() {
  const context = React.useContext(ToastContext)

  if (!context) {
    throw new Error("useToast must be used within an AppToastProvider")
  }

  return context
}

export { useToast, AppToastProvider }
