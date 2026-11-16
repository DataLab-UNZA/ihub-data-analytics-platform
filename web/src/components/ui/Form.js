import { cx } from '@/lib/format';

/** Label + control wrapper. Pass the control as children and give it the same `id`. */
export function Field({ id, label, hint, error, className, children }) {
  return (
    <div className={cx('field', className)}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      {children}
      {hint && (
        <p className="field__hint" id={`${id}-hint`}>
          {hint}
        </p>
      )}
      {error && (
        <p className="field__error" id={`${id}-error`}>
          {error}
        </p>
      )}
    </div>
  );
}

export function Input({ className, ...props }) {
  return <input className={cx('input', className)} {...props} />;
}

export function Textarea({ className, ...props }) {
  return <textarea className={cx('textarea', className)} {...props} />;
}

/** Native select styled as a form control. `options` are strings or [value, label] pairs. */
export function Select({ options, className, ...props }) {
  return (
    <select className={cx('select-box', className)} {...props}>
      {options.map((option) => {
        const [value, label] = Array.isArray(option) ? option : [option, option];
        return (
          <option key={value} value={value}>
            {label}
          </option>
        );
      })}
    </select>
  );
}

/** Compact select that looks like a link, used in toolbars. Options are strings or [value, label]. */
export function SelectLink({ options, label, ...props }) {
  return (
    <>
      <label className="sr-only" htmlFor={props.id}>
        {label}
      </label>
      <select className="select-link" {...props}>
        {options.map((option) => {
          const [value, text] = Array.isArray(option) ? option : [option, option];
          return (
            <option key={value} value={value}>
              {text}
            </option>
          );
        })}
      </select>
    </>
  );
}
