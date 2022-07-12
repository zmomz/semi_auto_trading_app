Vue.use(VueFormulate)

new Vue({
  el: '#app',
  delimiters: ['[[', ']]'],
  data: function () {
    return {
      values: {}
    }
  },
  methods: {
    async submitHandler() {
        const res = await fetch('/api/users',{
          method:'POST',
          headers:{
            'Content-type':'application/json',
          },
          body: JSON.stringify(this.values)
        })
        console.log(res)
        window.location.href = '/'
    }
  }
})


