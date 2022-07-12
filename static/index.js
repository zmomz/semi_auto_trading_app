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
        const res = await fetch('/',{
          method:'POST',
          headers:{
            'Content-type':'application/json',
          },
          body: JSON.stringify(this.values)
        })
        this.reset()
    },
    reset () {
      this.$formulate.reset('buycrypto')
    },
    redirect(){
      window.location.href = '/trades'
    }
  }
})
